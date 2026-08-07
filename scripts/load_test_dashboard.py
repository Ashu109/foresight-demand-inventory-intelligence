"""Simple load-test harness for the Streamlit dashboard entrypoint."""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_load_test(iterations: int = 3) -> list[float]:
    timings = []
    for _ in range(iterations):
        start = time.perf_counter()
        completed = subprocess.run(
            [sys.executable, "tests/smoke_forecast.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        elapsed = time.perf_counter() - start
        timings.append(elapsed)
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr or completed.stdout)
    return timings


if __name__ == "__main__":
    timings = run_load_test()
    print({"iterations": len(timings), "timings_seconds": timings, "avg_seconds": round(sum(timings)/len(timings), 3)})
