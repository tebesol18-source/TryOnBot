"""Validation tests: missing fields, invalid values, and the safety gates.

Covers Sprint 2 requirement 8: valid config, missing fields, invalid
values, empty admin IDs, null channel ID and missing BOT_TOKEN (the last
one lives in test_config_loader.py).
"""
from __future__ import annotations

import pytest

from faith_el import ConfigValidationError, load_configuration


def load(make_config_dir, settings=None, boutique=None):
    d = make_config_dir(settings=settings, boutique=boutique)
    return load_configuration(d)


# ---------------------------------------------------------------------------
# Missing required fields / sections
# ---------------------------------------------------------------------------
class TestMissingFields:
    def test_missing_privacy_section(self, make_config_dir, valid_settings_raw):
        del valid_settings_raw["privacy"]
        d = make_config_dir(settings=valid_settings_raw)
        with pytest.raises(ConfigValidationError) as exc:
            load_configuration(d)
        assert any("privacy" in p for p in exc.value.problems)

    def test_missing_required_key_in_retention(self, make_config_dir, valid_settings_raw):
        del valid_settings_raw["retention"]["max_local_retention_days"]
        # default of 7 is acceptable — but removing telegram note must fail
        del valid_settings_raw["retention"]["telegram_retention_note"]
        d = make_config_dir(settings=valid_settings_raw)
        with pytest.raises(ConfigValidationError) as exc:
            load_configuration(d)
        assert any("telegram_retention_note" in p for p in exc.value.problems)

    def test_missing_boutique_section(self, make_config_dir):
        d = make_config_dir(boutique={})   # no 'boutique' key at all
        with pytest.raises(ConfigValidationError) as exc:
            load_configuration(d)
        assert any("boutique" in p for p in exc.value.problems)

    def test_missing_channel_section(self, make_config_dir, valid_boutique_raw):
        del valid_boutique_raw["channel"]
        d = make_config_dir(boutique=valid_boutique_raw)
        with pytest.raises(ConfigValidationError) as exc:
            load_configuration(d)
        assert any("channel" in p for p in exc.value.problems)


# ---------------------------------------------------------------------------
# Invalid values / types
# ---------------------------------------------------------------------------
class TestInvalidValues:
    def test_wrong_type_for_retention_days(self, make_config_dir, valid_settings_raw):
        valid_settings_raw["retention"]["max_local_retention_days"] = "seven"
        d = make_config_dir(settings=valid_settings_raw)
        with pytest.raises(ConfigValidationError) as exc:
            load_configuration(d)
        assert any("max_local_retention_days" in p for p in exc.value.problems)

    def test_retention_days_too_high(self, make_config_dir, valid_settings_raw):
        valid_settings_raw["retention"]["max_local_retention_days"] = 365
        d = make_config_dir(settings=valid_settings_raw)
        with pytest.raises(ConfigValidationError) as exc:
            load_configuration(d)
        assert any("between" in p for p in exc.value.problems)

    def test_bad_log_level(self, make_config_dir, valid_settings_raw):
        valid_settings_raw["logging"]["level"] = "LOUD"
        d = make_config_dir(settings=valid_settings_raw)
        with pytest.raises(ConfigValidationError) as exc:
            load_configuration(d)
        assert any("logging.level" in p for p in exc.value.problems)

    def test_non_aiogram_framework_rejected(self, make_config_dir, valid_settings_raw):
        valid_settings_raw["telegram"]["framework"] = "telethon"
        d = make_config_dir(settings=valid_settings_raw)
        with pytest.raises(ConfigValidationError) as exc:
            load_configuration(d)
        assert any("aiogram" in p for p in exc.value.problems)

    def test_aiogram_2x_version_rejected(self, make_config_dir, valid_settings_raw):
        valid_settings_raw["telegram"]["framework_version"] = ">=2.0,<3.0"
        d = make_config_dir(settings=valid_settings_raw)
        with pytest.raises(ConfigValidationError) as exc:
            load_configuration(d)
        assert any("3.x" in p for p in exc.value.problems)

    def test_invalid_boutique_id_slug(self, make_config_dir, valid_boutique_raw):
        valid_boutique_raw["boutique"]["id"] = "Faith EL!!"
        d = make_config_dir(boutique=valid_boutique_raw)
        with pytest.raises(ConfigValidationError) as exc:
            load_configuration(d)
        assert any("boutique.id" in p for p in exc.value.problems)

    def test_two_boutiques_rejected(self, make_config_dir):
        d = make_config_dir(boutique={"boutiques": [
            {"id": "a-one", "name": "A"}, {"id": "b-two", "name": "B"}]})
        with pytest.raises(ConfigValidationError) as exc:
            load_configuration(d)
        assert any("EXACTLY ONE" in p or "boutiques" in p for p in exc.value.problems)

    def test_non_mock_provider_rejected(self, make_config_dir, valid_settings_raw):
        valid_settings_raw["imagegen"]["provider"] = "stable-diffusion-api"
        d = make_config_dir(settings=valid_settings_raw)
        with pytest.raises(ConfigValidationError) as exc:
            load_configuration(d)
        assert any("mock" in p for p in exc.value.problems)

    def test_extra_allowed_provider_rejected(self, make_config_dir, valid_settings_raw):
        valid_settings_raw["imagegen"]["providers_allowed"] = ["mock", "paid-vision-api"]
        d = make_config_dir(settings=valid_settings_raw)
        with pytest.raises(ConfigValidationError) as exc:
            load_configuration(d)
        assert any("providers_allowed" in p for p in exc.value.problems)

    def test_training_on_photos_rejected(self, make_config_dir, valid_settings_raw):
        valid_settings_raw["privacy"]["use_photos_for_model_training"] = True
        d = make_config_dir(settings=valid_settings_raw)
        with pytest.raises(ConfigValidationError) as exc:
            load_configuration(d)
        assert any("train" in p for p in exc.value.problems)

    def test_consent_gate_cannot_be_disabled(self, make_config_dir, valid_settings_raw):
        valid_settings_raw["privacy"]["require_customer_consent_before_download"] = False
        d = make_config_dir(settings=valid_settings_raw)
        with pytest.raises(ConfigValidationError) as exc:
            load_configuration(d)
        assert any("mandatory privacy/safety rule" in p for p in exc.value.problems)

    def test_immediate_deletion_cannot_be_disabled(self, make_config_dir, valid_settings_raw):
        valid_settings_raw["retention"]["immediate_deletion_on_request"] = False
        d = make_config_dir(settings=valid_settings_raw)
        with pytest.raises(ConfigValidationError) as exc:
            load_configuration(d)
        assert any("immediate_deletion_on_request" in p for p in exc.value.problems)

    def test_deletion_scope_must_cover_all_three(self, make_config_dir, valid_settings_raw):
        valid_settings_raw["retention"]["deletion_scope"] = ["original_photos"]
        d = make_config_dir(settings=valid_settings_raw)
        with pytest.raises(ConfigValidationError) as exc:
            load_configuration(d)
        msg = " ".join(exc.value.problems)
        assert "generated_previews" in msg and "database_records" in msg

    def test_paid_api_policy_flag_cannot_be_false(self, make_config_dir, valid_settings_raw):
        valid_settings_raw["policy"]["no_paid_apis"] = False
        d = make_config_dir(settings=valid_settings_raw)
        with pytest.raises(ConfigValidationError):
            load_configuration(d)


# ---------------------------------------------------------------------------
# Safety gate: channel monitoring vs channel id
# ---------------------------------------------------------------------------
class TestChannelSafetyGate:
    def test_null_id_with_requested_true_stays_disabled(self, make_config_dir, valid_boutique_raw):
        """THE critical test: YAML asks to enable monitoring while id is null."""
        valid_boutique_raw["channel"]["monitoring_enabled"] = True  # sneaky/erroneous
        valid_boutique_raw["channel"]["id"] = None
        cfg = load(make_config_dir, boutique=valid_boutique_raw)
        assert cfg.boutique.channel.monitoring_requested is True
        assert cfg.boutique.channel.monitoring_effective is False
        assert any("channel" in w.lower() for w in cfg.warnings)

    def test_garbage_id_cannot_enable_monitoring(self, make_config_dir, valid_boutique_raw):
        valid_boutique_raw["channel"]["monitoring_enabled"] = True
        valid_boutique_raw["channel"]["id"] = "not-a-number"
        d = make_config_dir(boutique=valid_boutique_raw)
        with pytest.raises(ConfigValidationError):
            load_configuration(d)

    def test_positive_id_rejected_as_invalid_channel(self, make_config_dir, valid_boutique_raw):
        valid_boutique_raw["channel"]["monitoring_enabled"] = True
        valid_boutique_raw["channel"]["id"] = 123456789
        d = make_config_dir(boutique=valid_boutique_raw)
        with pytest.raises(ConfigValidationError) as exc:
            load_configuration(d)
        assert any("negative" in p or "-100" in p for p in exc.value.problems)

    def test_valid_negative_id_enables_monitoring(self, make_config_dir, valid_boutique_raw):
        valid_boutique_raw["channel"]["id"] = -1001234567890
        valid_boutique_raw["channel"]["monitoring_enabled"] = True
        cfg = load(make_config_dir, boutique=valid_boutique_raw)
        assert cfg.boutique.channel.monitoring_effective is True

    def test_quoted_numeric_id_accepted(self, make_config_dir, valid_boutique_raw):
        valid_boutique_raw["channel"]["id"] = "-1001234567890"   # string in YAML
        valid_boutique_raw["channel"]["monitoring_enabled"] = True
        cfg = load(make_config_dir, boutique=valid_boutique_raw)
        assert cfg.boutique.channel.id == -1001234567890
        assert cfg.boutique.channel.monitoring_effective is True


# ---------------------------------------------------------------------------
# Safety gate: admin functions vs admin ids
# ---------------------------------------------------------------------------
class TestAdminSafetyGate:
    def test_empty_ids_with_requested_true_stays_disabled(self, make_config_dir, valid_boutique_raw):
        """THE critical test: YAML asks to enable admin functions with [] ids."""
        valid_boutique_raw["admins"]["admin_functions_enabled"] = True
        valid_boutique_raw["admins"]["telegram_user_ids"] = []
        cfg = load(make_config_dir, boutique=valid_boutique_raw)
        assert cfg.boutique.admins.admin_functions_requested is True
        assert cfg.boutique.admins.admin_functions_effective is False
        assert any("admin" in w.lower() for w in cfg.warnings)

    def test_garbage_ids_cannot_enable_admin(self, make_config_dir, valid_boutique_raw):
        valid_boutique_raw["admins"]["admin_functions_enabled"] = True
        valid_boutique_raw["admins"]["telegram_user_ids"] = ["abc", None]
        d = make_config_dir(boutique=valid_boutique_raw)
        with pytest.raises(ConfigValidationError):
            load_configuration(d)

    def test_zero_and_negative_ids_rejected(self, make_config_dir, valid_boutique_raw):
        valid_boutique_raw["admins"]["admin_functions_enabled"] = True
        valid_boutique_raw["admins"]["telegram_user_ids"] = [0, -5]
        d = make_config_dir(boutique=valid_boutique_raw)
        with pytest.raises(ConfigValidationError) as exc:
            load_configuration(d)
        assert any("positive" in p for p in exc.value.problems)

    def test_valid_ids_enable_admin(self, make_config_dir, valid_boutique_raw):
        valid_boutique_raw["admins"]["telegram_user_ids"] = [123456789]
        valid_boutique_raw["admins"]["admin_functions_enabled"] = True
        cfg = load(make_config_dir, boutique=valid_boutique_raw)
        assert cfg.boutique.admins.valid_user_ids == (123456789,)
        assert cfg.boutique.admins.admin_functions_effective is True

    def test_valid_ids_but_not_requested_stays_disabled(self, make_config_dir, valid_boutique_raw):
        valid_boutique_raw["admins"]["telegram_user_ids"] = [123456789]
        valid_boutique_raw["admins"]["admin_functions_enabled"] = False
        cfg = load(make_config_dir, boutique=valid_boutique_raw)
        assert cfg.boutique.admins.admin_functions_effective is False


# ---------------------------------------------------------------------------
# Secrets never leak through validation errors
# ---------------------------------------------------------------------------
class TestNoSecretLeakage:
    def test_error_messages_contain_no_token_like_values(self, make_config_dir, valid_settings_raw):
        secret = "123456:AAA-BBB-CCCsecrettoken"
        valid_settings_raw["app"]["name"] = secret          # put a token-shaped value in YAML
        d = make_config_dir(settings=valid_settings_raw)
        try:
            load_configuration(d)
        except Exception as exc:                              # whatever error occurs
            assert secret not in str(exc)
        # (config may actually be valid here; that's fine — nothing printed)
