"""Simple health probe for cloud deployment."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
print(f"Health OK from {ROOT}")
