"""Simple local quality-check entry point for CI."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> None:
    print("$", " ".join(command))
    completed = subprocess.run(command, cwd=ROOT, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def main() -> None:
    run([sys.executable, "tests/smoke_forecast.py"])

    pytest = shutil.which("pytest")
    if pytest:
        run([sys.executable, "-m", "pytest", "tests/test_config.py"])
    else:
        print("pytest not installed; skipping pytest step")

    flake8 = shutil.which("flake8")
    if flake8:
        run([flake8, "app.py", "dashboard", "modules", "utils", "config", "tests", "--max-line-length=120"])
    else:
        print("flake8 not installed; skipping lint step")


if __name__ == "__main__":
    main()
