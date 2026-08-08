"""Lightweight smoke test that runs inside the container build to validate imports."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.ml_module import available_models  # noqa: E402


def main() -> None:
    models = available_models()
    print("SMOKE: available models ->", models)


if __name__ == "__main__":
    main()
