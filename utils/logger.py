"""Simple centralized logger configuration."""
from __future__ import annotations

import logging
import os
import sys
from typing import Optional


def _level_from_env(default: str = "INFO") -> int:
    level_name = os.getenv("LOG_LEVEL", default)
    return getattr(logging, level_name.upper(), logging.INFO)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    name = name or __name__
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(stream=sys.stderr)
        formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(_level_from_env())
    return logger
