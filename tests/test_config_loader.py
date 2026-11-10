"""Tests for the Faith-EL configuration loader — happy paths & file errors."""
from __future__ import annotations

import pytest

from faith_el import (
    ConfigFileError,
    SecretNotConfiguredError,
    get_bot_token,
    load_configuration,
    require_bot_token,
)

REPO_CONFIG = pytest.fixture  # noqa: F841  (keep linters quiet about unused import alias)


class TestValidConfiguration:
    def test_repo_config_loads_cleanly(self):
        """The real committed config must always pass validation."""
        cfg = load_configuration()
        assert cfg.settings.app.name == "faith-el-virtual-stylist"
        assert cfg.boutique.config.id == "faith-el-main"

    def test_single_boutique_enforced(self):
        cfg = load_configuration()
        # exactly one boutique object exists; multi-boutique lists are rejected elsewhere
        assert cfg.settings.policy.single_boutique_only is True
        assert cfg.boutique.config.active is True

    def test_retention_defaults(self):
        cfg = load_configuration()
        r = cfg.settings.retention
        assert r.max_local_retention_days == 7
        assert r.immediate_deletion_on_request is True
        assert set(r.deletion_scope) >= {
            "original_photos", "generated_previews", "database_records"}
        assert "Telegram" in r.telegram_retention_note

    def test_privacy_rules(self):
        p = load_configuration().settings.privacy
        assert p.require_customer_consent_before_download is True
        assert p.consent_scope.download_photo is True
        assert p.consent_scope.process_photo is True
        assert p.use_photos_for_model_training is False
        assert p.training_data_prohibited is True

    def test_mock_provider_only(self):
        ig = load_configuration().settings.imagegen
        assert ig.provider == "mock"
        assert ig.providers_allowed == ("mock",)
        assert ig.label_mock_outputs is True
        assert "mock" in ig.mock_output_label.lower()

    def test_channel_and_admin_disabled_by_default(self):
        cfg = load_configuration()
        assert cfg.boutique.channel.id is None
        assert cfg.boutique.channel.monitoring_effective is False
        assert cfg.boutique.admins.valid_user_ids == ()
        assert cfg.boutique.admins.admin_functions_effective is False


class TestFileErrors:
    def test_missing_settings_file(self, tmp_path):
        d = tmp_path / "config"
        d.mkdir()
        with pytest.raises(ConfigFileError, match="settings.yaml"):
            load_configuration(d)

    def test_invalid_yaml(self, make_config_dir, valid_boutique_raw):
        bad = make_config_dir(boutique=valid_boutique_raw)
        (bad / "settings.yaml").write_text("app: [unclosed", encoding="utf-8")
        with pytest.raises(ConfigFileError, match="not valid YAML"):
            load_configuration(bad)

    def test_top_level_not_mapping(self, make_config_dir):
        bad = make_config_dir()
        (bad / "settings.yaml").write_text("- just\n- a list\n", encoding="utf-8")
        with pytest.raises(ConfigFileError, match="mapping"):
            load_configuration(bad)


class TestBotTokenFromEnvironment:
    def test_load_does_not_require_token(self, monkeypatch):
        monkeypatch.delenv("BOT_TOKEN", raising=False)
        cfg = load_configuration()          # must NOT raise
        assert get_bot_token(cfg, env={}) is None

    def test_get_bot_token_reads_env_only(self):
        cfg = load_configuration()
        fake = {"BOT_TOKEN": "1234:FAKE-FOR-TESTS-ONLY"}
        assert get_bot_token(cfg, env=fake) == "1234:FAKE-FOR-TESTS-ONLY"

    def test_require_bot_token_raises_without_value_in_message(self, monkeypatch):
        monkeypatch.delenv("BOT_TOKEN", raising=False)
        cfg = load_configuration()
        with pytest.raises(SecretNotConfiguredError) as excinfo:
            require_bot_token(cfg, env={})
        msg = str(excinfo.value)
        assert "BOT_TOKEN" in msg                 # names the variable
        assert "1234" not in msg                  # never shows any value

    def test_token_never_stored_on_config_objects(self):
        cfg = load_configuration()
        # serialising the whole config must not contain a token-shaped string
        import dataclasses, json
        dump = json.dumps(dataclasses.asdict(cfg), default=str)
        assert "BOT_TOKEN" in dump                       # env var NAME is fine to store
        assert "bot_token" not in {f.name for f in dataclasses.fields(cfg.settings.telegram)}
