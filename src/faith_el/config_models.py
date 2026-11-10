"""Typed, immutable configuration objects for Faith-EL Virtual Stylist.

These are plain dataclasses (no third-party validation library needed).
They are produced by :mod:`faith_el.config_loader` AFTER all validation
has passed, so any instance you hold is guaranteed to be safe/consistent.

Effective-safety rule: ``channel_monitoring_enabled`` and
``admin_functions_enabled`` are *computed* from the raw YAML plus the
policy rules — a config file can never claim "enabled" on its own if the
required IDs are missing or invalid.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AppConfig:
    name: str
    version: str
    python_min_version: str
    environment: str  # development | production


@dataclass(frozen=True)
class TelegramConfig:
    framework: str            # must be "aiogram"
    framework_version: str    # must be an aiogram 3.x specifier
    bot_token_env_var: str    # name of env var holding the token ("BOT_TOKEN")
    # NOTE: the token VALUE lives only in the process environment. It is
    # deliberately NOT stored on this object, so printing/serialising the
    # config can never leak it.


@dataclass(frozen=True)
class StorageConfig:
    base_dir: str
    photos_dir: str
    previews_dir: str
    database_path: str


@dataclass(frozen=True)
class ImageGenConfig:
    provider: str                 # "mock" only for MVP
    providers_allowed: tuple[str, ...]
    label_mock_outputs: bool
    mock_output_label: str


@dataclass(frozen=True)
class ConsentScope:
    download_photo: bool
    process_photo: bool


@dataclass(frozen=True)
class PrivacyConfig:
    require_customer_consent_before_download: bool
    consent_scope: ConsentScope
    use_photos_for_model_training: bool   # must always be False
    training_data_prohibited: bool        # must always be True


@dataclass(frozen=True)
class RetentionConfig:
    max_local_retention_days: int          # default 7
    cleanup_schedule_hours: int
    immediate_deletion_on_request: bool    # must always be True
    deletion_scope: tuple[str, ...]        # original_photos, generated_previews, database_records
    telegram_retention_note: str


@dataclass(frozen=True)
class PolicyConfig:
    require_valid_ids_before_enable: bool
    single_boutique_only: bool
    no_paid_apis: bool


@dataclass(frozen=True)
class LoggingConfig:
    level: str
    redact_tokens: bool  # must always be True


@dataclass(frozen=True)
class Settings:
    app: AppConfig
    telegram: TelegramConfig
    storage: StorageConfig
    imagegen: ImageGenConfig
    privacy: PrivacyConfig
    retention: RetentionConfig
    policy: PolicyConfig
    logging: LoggingConfig


@dataclass(frozen=True)
class BoutiqueConfig:
    id: str
    name: str
    display_name: str
    locale: str
    currency: str
    active: bool


@dataclass(frozen=True)
class ChannelConfig:
    id: int | None
    username: str | None
    monitoring_requested: bool          # raw value from YAML
    monitoring_effective: bool          # computed — see safety rules


@dataclass(frozen=True)
class AdminsConfig:
    valid_user_ids: tuple[int, ...]     # validated positive ints only
    admin_functions_requested: bool     # raw value from YAML
    admin_functions_effective: bool     # computed — see safety rules


@dataclass(frozen=True)
class CatalogConfig:
    source: str      # "local" only for MVP
    path: str


@dataclass(frozen=True)
class Boutique:
    config: BoutiqueConfig
    channel: ChannelConfig
    admins: AdminsConfig
    catalog: CatalogConfig


@dataclass(frozen=True)
class AppConfiguration:
    """Everything a later sprint needs, fully validated."""

    settings: Settings
    boutique: Boutique
    warnings: tuple[str, ...] = field(default_factory=tuple)
