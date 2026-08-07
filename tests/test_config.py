from __future__ import annotations

from config.settings import load_config


def test_config_contains_app_name() -> None:
    cfg = load_config()
    assert cfg["app"]["name"] == "Forsight"
