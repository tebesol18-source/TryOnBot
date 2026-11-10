"""Configuration loader & validator for Faith-EL Virtual Stylist (Sprint 2).

Responsibilities
----------------
1. Read ``config/settings.yaml`` and ``config/boutique.yaml`` (YAML only,
   PyYAML safe_load — never ``yaml.load``).
2. Validate required fields, types and allowed values.
3. Enforce the MVP safety policy:
   - exactly ONE boutique;
   - valid boutique id (slug);
   - channel monitoring can only be effectively enabled with a valid
     numeric channel id AND policy validation;
   - admin functions can only be effectively enabled with at least one
     valid positive integer Telegram user id;
   - mock is the ONLY permitted image provider;
   - consent + retention + no-training privacy rules are non-negotiable.
4. Expose BOT_TOKEN via the environment name only. Loading/testing the
   configuration NEVER requires a real token and NEVER prints secrets.

Public API
----------
``load_configuration(config_dir=None, env=None)`` -> AppConfiguration
``get_bot_token(settings, env=None)``             -> str | None
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Mapping

import yaml

from .config_models import (
    AdminsConfig,
    AppConfig,
    AppConfiguration,
    Boutique,
    BoutiqueConfig,
    CatalogConfig,
    ChannelConfig,
    ConsentScope,
    ImageGenConfig,
    LoggingConfig,
    PolicyConfig,
    PrivacyConfig,
    RetentionConfig,
    Settings,
    StorageConfig,
    TelegramConfig,
)
from .utils.errors import ConfigFileError, ConfigValidationError, SecretNotConfiguredError

# --------------------------------------------------------------------------
# Constants encoding the approved MVP policy
# --------------------------------------------------------------------------
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}$")
TELEGRAM_ID_RE = re.compile(r"^-?\d+$")          # raw YAML may quote ids
ALLOWED_ENVIRONMENTS = ("development", "production")
ALLOWED_LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
ALLOWED_PROVIDERS = ("mock",)                    # MVP: mock ONLY
REQUIRED_DELETION_SCOPE = ("original_photos", "generated_previews", "database_records")
MIN_RETENTION_DAYS, MAX_RETENTION_DAYS = 1, 30   # 7 is the default; longer is not allowed

DEFAULT_CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


# --------------------------------------------------------------------------
# Low-level helpers
# --------------------------------------------------------------------------
def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ConfigFileError(f"Configuration file not found: {path}")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigFileError(f"Could not read {path.name}: {exc.strerror or exc}") from exc
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        # MarkedYAMLError strings contain file content lines but never
        # secrets (secrets live in the environment, not in YAML).
        raise ConfigFileError(f"{path.name} is not valid YAML: {exc}") from exc
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ConfigFileError(f"{path.name}: top level must be a mapping of keys to values.")
    return data


def _need(problems: list[str], section: list[Any] | None, name: str) -> dict[str, Any]:
    """Return a required mapping section or record a problem."""
    if not isinstance(section, dict):
        problems.append(f"[{name}] section is missing or is not a mapping.")
        return {}
    return section


def _get(problems: list[str], where: str, section: dict[str, Any], key: str,
         expected: tuple[type, ...], *, default: Any = ..., allow_none: bool = False) -> Any:
    """Fetch a required value with type checking; record problems (no crash)."""
    if key not in section:
        if default is not ...:
            return default
        problems.append(f"{where}.{key} is missing.")
        return None
    value = section[key]
    if value is None:
        if allow_none:
            return None
        problems.append(f"{where}.{key} must be set (found null).")
        return None
    if not isinstance(value, expected):
        type_names = "/".join(t.__name__ for t in expected)
        problems.append(f"{where}.{key} has wrong type: expected {type_names}.")
        return None
    return value


def _as_bool(problems: list[str], where: str, section: dict[str, Any], key: str,
              *, required_true: bool = False) -> bool:
    value = _get(problems, where, section, key, (bool,))
    if value is None and key not in section:
        return False
    if value is None:
        value = False
    if required_true and value is not True:
        problems.append(
            f"{where}.{key} must be true — this is a mandatory privacy/safety rule."
        )
    return bool(value)


def _parse_int(problems: list[str], where: str, key: str, value: Any) -> int | None:
    """Accept genuine ints or clean numeric strings (YAML quoting safety)."""
    if isinstance(value, bool):
        problems.append(f"{where}.{key} must be an integer, not a boolean.")
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and TELEGRAM_ID_RE.match(value.strip()):
        return int(value.strip())
    problems.append(f"{where}.{key} must be an integer.")
    return None


# --------------------------------------------------------------------------
# settings.yaml validation
# --------------------------------------------------------------------------
def _validate_settings(raw: dict[str, Any]) -> tuple[Settings, list[str]]:
    problems: list[str] = []

    app_raw = _need(problems, raw.get("app"), "app")
    app = AppConfig(
        name=_get(problems, "app", app_raw, "name", (str, "")) or "",
        version=_get(problems, "app", app_raw, "version", (str,), default="0.0.0") or "0.0.0",
        python_min_version=_get(problems, "app", app_raw, "python_min_version", (str,), default="3.11") or "3.11",
        environment=_get(problems, "app", app_raw, "environment", (str,), default="development") or "development",
    )
    if app.environment not in ALLOWED_ENVIRONMENTS:
        problems.append(f"app.environment must be one of {ALLOWED_ENVIRONMENTS}.")

    tg_raw = _need(problems, raw.get("telegram"), "telegram")
    telegram = TelegramConfig(
        framework=_get(problems, "telegram", tg_raw, "framework", (str,), default="aiogram") or "",
        framework_version=_get(problems, "telegram", tg_raw, "framework_version", (str,), default="") or "",
        bot_token_env_var=_get(problems, "telegram", tg_raw, "bot_token_env_var", (str,), default="BOT_TOKEN") or "BOT_TOKEN",
    )
    if telegram.framework != "aiogram":
        problems.append("telegram.framework must be 'aiogram' (approved architecture).")
    # framework_version must pin aiogram 3.x: reject any constraint that
    # would allow a major version other than 3.
    fv = telegram.framework_version or ""
    m = re.search(r">=\s*(\d+)\.(\d+)", fv)
    u = re.search(r"<\s*(\d+)(?:\.(\d+))?", fv)
    lower_ok = bool(m) and m.group(1) == "3"
    upper_ok = (not u) or (u.group(1) == "4" and (u.group(2) is None or u.group(2) == "0"))
    if fv and not (lower_ok and upper_ok):
        problems.append(
            "telegram.framework_version must restrict aiogram to the 3.x series "
            f"(got {fv!r}; expected e.g. '>=3.0,<4.0')."
        )

    st_raw = _need(problems, raw.get("storage"), "storage")
    storage = StorageConfig(
        base_dir=_get(problems, "storage", st_raw, "base_dir", (str,), default="data") or "data",
        photos_dir=_get(problems, "storage", st_raw, "photos_dir", (str,), default="data/photos") or "data/photos",
        previews_dir=_get(problems, "storage", st_raw, "previews_dir", (str,), default="data/previews") or "data/previews",
        database_path=_get(problems, "storage", st_raw, "database_path", (str,), default="data/db/faith_el.sqlite") or "",
    )

    ig_raw = _need(problems, raw.get("imagegen"), "imagegen")
    allowed = _get(problems, "imagegen", ig_raw, "providers_allowed", (list,), default=["mock"]) or ["mock"]
    allowed_t = tuple(str(a) for a in allowed)
    provider = _get(problems, "imagegen", ig_raw, "provider", (str,), default="mock") or ""
    label = _get(problems, "imagegen", ig_raw, "mock_output_label", (str,), default="") or ""
    imagegen = ImageGenConfig(
        provider=provider,
        providers_allowed=allowed_t,
        label_mock_outputs=_as_bool(problems, "imagegen", ig_raw, "label_mock_outputs", required_true=True),
        mock_output_label=label,
    )
    if provider not in ALLOWED_PROVIDERS:
        problems.append(
            f"imagegen.provider must be 'mock' for the MVP (got {provider!r}). "
            "Paid APIs / GPU services are prohibited."
        )
    if set(allowed_t) - set(ALLOWED_PROVIDERS):
        problems.append("imagegen.providers_allowed may only contain: mock.")
    if provider == "mock" and imagegen.label_mock_outputs and not label.strip():
        problems.append("imagegen.mock_output_label must be a non-empty warning label.")

    pv_raw = _need(problems, raw.get("privacy"), "privacy")
    cs_raw = pv_raw.get("consent_scope") if isinstance(pv_raw.get("consent_scope"), dict) else {}
    if "consent_scope" in pv_raw and not isinstance(pv_raw["consent_scope"], dict):
        problems.append("privacy.consent_scope must be a mapping.")
    privacy = PrivacyConfig(
        require_customer_consent_before_download=_as_bool(
            problems, "privacy", pv_raw, "require_customer_consent_before_download", required_true=True),
        consent_scope=ConsentScope(
            download_photo=_as_bool(problems, "privacy.consent_scope", cs_raw, "download_photo", required_true=True),
            process_photo=_as_bool(problems, "privacy.consent_scope", cs_raw, "process_photo", required_true=True),
        ),
        use_photos_for_model_training=_get(problems, "privacy", pv_raw, "use_photos_for_model_training", (bool,), default=False),
        training_data_prohibited=_as_bool(problems, "privacy", pv_raw, "training_data_prohibited", required_true=True),
    )
    if privacy.use_photos_for_model_training is not False:
        problems.append("privacy.use_photos_for_model_training MUST be false — customer photos may never train models.")

    rt_raw = _need(problems, raw.get("retention"), "retention")
    days_val = _get(problems, "retention", rt_raw, "max_local_retention_days", (int, str), default=7)
    days = _parse_int(problems, "retention", "max_local_retention_days", days_val)
    if days is not None and not (MIN_RETENTION_DAYS <= days <= MAX_RETENTION_DAYS):
        problems.append(
            f"retention.max_local_retention_days must be between "
            f"{MIN_RETENTION_DAYS} and {MAX_RETENTION_DAYS} (default 7)."
        )
    hours_val = _get(problems, "retention", rt_raw, "cleanup_schedule_hours", (int, str), default=24)
    hours = _parse_int(problems, "retention", "cleanup_schedule_hours", hours_val)
    if hours is not None and not (1 <= hours <= 168):
        problems.append("retention.cleanup_schedule_hours must be between 1 and 168.")
    scope_val = _get(problems, "retention", rt_raw, "deletion_scope", (list,), default=[]) or []
    scope_t = tuple(str(s) for s in scope_val)
    missing_scope = [s for s in REQUIRED_DELETION_SCOPE if s not in scope_t]
    if missing_scope:
        problems.append(
            "retention.deletion_scope must cover: " + ", ".join(missing_scope)
            + " (deletion must remove originals, previews AND database records)."
        )
    note = _get(problems, "retention", rt_raw, "telegram_retention_note", (str,), default="") or ""
    if not note.strip():
        problems.append("retention.telegram_retention_note must explain Telegram's own retention limits.")
    retention = RetentionConfig(
        max_local_retention_days=days if days is not None else 0,
        cleanup_schedule_hours=hours if hours is not None else 0,
        immediate_deletion_on_request=_as_bool(
            problems, "retention", rt_raw, "immediate_deletion_on_request", required_true=True),
        deletion_scope=scope_t,
        telegram_retention_note=note.strip(),
    )

    po_raw = _need(problems, raw.get("policy"), "policy")
    policy = PolicyConfig(
        require_valid_ids_before_enable=_as_bool(
            problems, "policy", po_raw, "require_valid_ids_before_enable", required_true=True),
        single_boutique_only=_as_bool(problems, "policy", po_raw, "single_boutique_only", required_true=True),
        no_paid_apis=_as_bool(problems, "policy", po_raw, "no_paid_apis", required_true=True),
    )

    lg_raw = _need(problems, raw.get("logging"), "logging")
    level = (_get(problems, "logging", lg_raw, "level", (str,), default="INFO") or "INFO").upper()
    logging_cfg = LoggingConfig(
        level=level,
        redact_tokens=_as_bool(problems, "logging", lg_raw, "redact_tokens", required_true=True),
    )
    if level not in ALLOWED_LOG_LEVELS:
        problems.append(f"logging.level must be one of {ALLOWED_LOG_LEVELS}.")

    settings = Settings(app=app, telegram=telegram, storage=storage, imagegen=imagegen,
                        privacy=privacy, retention=retention, policy=policy, logging=logging_cfg)
    return settings, problems


# --------------------------------------------------------------------------
# boutique.yaml validation (exactly one boutique)
# --------------------------------------------------------------------------
def _validate_boutique(raw: dict[str, Any], policy: PolicyConfig) -> tuple[Boutique, list[str]]:
    problems: list[str] = []
    warnings: list[str] = []

    # --- Exactly one boutique -------------------------------------------
    if "boutiques" in raw:
        items = raw["boutiques"]
        n = len(items) if isinstance(items, (list, dict)) else 1
        problems.append(
            f"boutique.yaml defines a 'boutiques' list with {n} entries. "
            "The MVP supports EXACTLY ONE boutique via the singular 'boutique:' key."
        )
        raise ConfigValidationError(problems)
    if not isinstance(raw.get("boutique"), dict):
        problems.append("[boutique] section is missing. Exactly one boutique must be configured.")
        raise ConfigValidationError(problems)

    b_raw = raw["boutique"]
    bid = _get(problems, "boutique", b_raw, "id", (str,), default="") or ""
    if not SLUG_RE.match(bid or ""):
        problems.append(
            "boutique.id must be a slug: lowercase letters/digits/hyphens, "
            "2-63 chars, starting with a letter or digit."
        )
    bc = BoutiqueConfig(
        id=bid,
        name=_get(problems, "boutique", b_raw, "name", (str,), default="") or "",
        display_name=_get(problems, "boutique", b_raw, "display_name", (str,), default="") or "",
        locale=_get(problems, "boutique", b_raw, "locale", (str,), default="en") or "en",
        currency=_get(problems, "boutique", b_raw, "currency", (str,), default="USD") or "USD",
        active=_as_bool(problems, "boutique", b_raw, "active"),
    )
    if not bc.name.strip():
        problems.append("boutique.name must be a non-empty string.")

    # --- Channel ---------------------------------------------------------
    ch_raw = _need(problems, raw.get("channel"), "channel")
    ch_id_val = ch_raw.get("id", None)
    ch_id: int | None = None
    ch_id_valid = False
    if ch_id_val is None:
        ch_id = None  # legitimately "not configured"
    else:
        ch_id = _parse_int(problems, "channel", "id", ch_id_val)
        # Telegram supergroup/channel ids are negative and start with -100…
        if ch_id is not None and ch_id > 0:
            problems.append("channel.id must be a negative Telegram channel id (e.g. -1001234567890).")
            ch_id = None
        if ch_id is not None and not str(ch_id).startswith("-100"):
            problems.append(
                "channel.id looks invalid: Telegram channels start with -100 "
                "(e.g. -1001234567890). Monitoring will stay disabled."
            )
            ch_id = None
        if ch_id is not None:
            ch_id_valid = True
    username = ch_raw.get("username", None)
    if username is not None and not isinstance(username, str):
        problems.append("channel.username must be a string like '@faith_el_showroom' or null.")
        username = None
    requested = bool(ch_raw.get("monitoring_enabled", False))
    if "monitoring_enabled" in ch_raw and not isinstance(ch_raw["monitoring_enabled"], bool):
        problems.append("channel.monitoring_enabled must be true/false.")
        requested = False
    # SAFETY: effective enablement requires a VALID id (+ policy gate).
    effective = requested and ch_id_valid and policy.require_valid_ids_before_enable is True \
        and ch_id is not None
    if requested and not effective:
        warnings.append(
            "channel.monitoring_enabled was requested but remains DISABLED: "
            "no valid channel.id is configured (policy.require_valid_ids_before_enable)."
        )
    channel = ChannelConfig(id=ch_id, username=username,
                            monitoring_requested=requested, monitoring_effective=effective)

    # --- Admins ------------------------------------------------------------
    ad_raw = _need(problems, raw.get("admins"), "admins")
    ids_val = _get(problems, "admins", ad_raw, "telegram_user_ids", (list,), default=[]) or []
    valid_ids: list[int] = []
    for i, item in enumerate(ids_val):
        v = _parse_int(problems, f"admins.telegram_user_ids[{i}]", "value", item)
        if v is None:
            continue
        if v <= 0:
            problems.append(f"admins.telegram_user_ids[{i}] must be a positive Telegram user id.")
            continue
        valid_ids.append(v)
    requested_admin = bool(ad_raw.get("admin_functions_enabled", False))
    if "admin_functions_enabled" in ad_raw and not isinstance(ad_raw["admin_functions_enabled"], bool):
        problems.append("admins.admin_functions_enabled must be true/false.")
        requested_admin = False
    # SAFETY: needs at least one VALID id; empty/garbage lists can never enable it.
    admin_effective = requested_admin and bool(valid_ids)
    if requested_admin and not admin_effective:
        warnings.append(
            "admins.admin_functions_enabled was requested but remains DISABLED: "
            "no valid telegram_user_ids are configured."
        )
    admins = AdminsConfig(valid_user_ids=tuple(valid_ids),
                          admin_functions_requested=requested_admin,
                          admin_functions_effective=admin_effective)

    # --- Catalog -----------------------------------------------------------
    cat_raw = _need(problems, raw.get("catalog"), "catalog")
    source = _get(problems, "catalog", cat_raw, "source", (str,), default="local") or "local"
    if source != "local":
        problems.append("catalog.source must be 'local' for the MVP (no paid APIs/services).")
    catalog = CatalogConfig(source=source,
                            path=_get(problems, "catalog", cat_raw, "path", (str,), default="data/catalog/") or "")

    boutique = Boutique(config=bc, channel=channel, admins=admins, catalog=catalog)
    if problems:
        raise ConfigValidationError(problems)
    return boutique, list(warnings)


def _empty_boutique() -> Boutique:
    return Boutique(
        config=BoutiqueConfig(id="", name="", display_name="", locale="en", currency="USD", active=False),
        channel=ChannelConfig(id=None, username=None, monitoring_requested=False, monitoring_effective=False),
        admins=AdminsConfig(valid_user_ids=(), admin_functions_requested=False, admin_functions_effective=False),
        catalog=CatalogConfig(source="local", path="data/catalog/"),
    )


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------
def load_configuration(
    config_dir: str | Path | None = None,
) -> AppConfiguration:
    """Load, parse and validate both YAML files. Raises ConfigError subclasses.

    Never touches the environment and never reads any secret.
    """
    directory = Path(config_dir) if config_dir is not None else DEFAULT_CONFIG_DIR
    settings_raw = _read_yaml(directory / "settings.yaml")
    boutique_raw = _read_yaml(directory / "boutique.yaml")

    settings, problems = _validate_settings(settings_raw)
    if problems:
        raise ConfigValidationError(problems)

    boutique, warnings = _validate_boutique(boutique_raw, settings.policy)
    if warnings and not boutique.config.id:
        raise ConfigValidationError(["boutique validation produced no usable configuration."])
    return AppConfiguration(settings=settings, boutique=boutique, warnings=tuple(warnings))


def get_bot_token(
    config: AppConfiguration | Settings,
    env: Mapping[str, str] | None = None,
) -> str | None:
    """Return the bot token from the environment, or None if unset.

    The value is never stored on config objects and never included in any
    message/log output.
    """
    settings = config.settings if isinstance(config, AppConfiguration) else config
    environ = os.environ if env is None else env
    return environ.get(settings.telegram.bot_token_env_var) or None


def require_bot_token(
    config: AppConfiguration | Settings,
    env: Mapping[str, str] | None = None,
) -> str:
    """Like :func:`get_bot_token` but raises if missing (for bot startup only).

    The error message names the variable only — never its value.
    """
    token = get_bot_token(config, env)
    if not token:
        settings = config.settings if isinstance(config, AppConfiguration) else config
        raise SecretNotConfiguredError(settings.telegram.bot_token_env_var)
    return token
