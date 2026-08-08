"""Data module package stub.

This package is a placeholder to separate data-related code from the UI and
ML logic. Importers can evolve these APIs to call into `scripts/` or
`dashboard/data.py` as the project modularizes further.
"""

from typing import List, Dict, Any


def list_data_sources() -> List[str]:
    return ["data/raw", "data/processed"]


def sample_manifest() -> Dict[str, Any]:
    return {"status": "ok"}


__all__ = ["list_data_sources", "sample_manifest"]
