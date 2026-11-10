"""Shared pytest fixtures for the Faith-EL test suite."""
from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO_ROOT / "config"

# Put src/ on sys.path so `import faith_el` works without packaging config.
import sys
sys.path.insert(0, str(REPO_ROOT / "src"))


def _load(name: str) -> dict:
    return yaml.safe_load((CONFIG_DIR / name).read_text(encoding="utf-8"))


@pytest.fixture()
def valid_settings_raw() -> dict:
    """A deep copy of the real, approved settings.yaml."""
    return copy.deepcopy(_load("settings.yaml"))


@pytest.fixture()
def valid_boutique_raw() -> dict:
    """A deep copy of the real, approved boutique.yaml."""
    return copy.deepcopy(_load("boutique.yaml"))


@pytest.fixture()
def make_config_dir(tmp_path):
    """Write settings/boutique dicts into a temp config dir; returns its path."""

    def _make(settings: dict | None = None, boutique: dict | None = None) -> Path:
        d = tmp_path / "config"
        d.mkdir(parents=True, exist_ok=True)
        if settings is not None:
            (d / "settings.yaml").write_text(
                yaml.safe_dump(settings, sort_keys=False), encoding="utf-8")
        else:
            (d / "settings.yaml").write_text(
                yaml.safe_dump(_load("settings.yaml"), sort_keys=False), encoding="utf-8")
        if boutique is not None:
            (d / "boutique.yaml").write_text(
                yaml.safe_dump(boutique, sort_keys=False), encoding="utf-8")
        else:
            (d / "boutique.yaml").write_text(
                yaml.safe_dump(_load("boutique.yaml"), sort_keys=False), encoding="utf-8")
        return d

    return _make
