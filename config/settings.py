"""Configuration loader for the project."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

BASE = Path(__file__).parent
CONFIG_FILE = BASE / "config.yaml"


def load_config() -> Dict[str, Any]:
    try:
        import yaml

        with open(CONFIG_FILE, "r", encoding="utf8") as fh:
            cfg = yaml.safe_load(fh) or {}
            return cfg
    except Exception:
        # Fallback minimal config
        return {"app": {"name": "Forsight"}, "logging": {"level": os.getenv("LOG_LEVEL", "INFO")}}


__all__ = ["load_config"]
