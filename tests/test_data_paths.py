from __future__ import annotations

from dashboard import data


def test_data_root_can_be_overridden(monkeypatch, tmp_path) -> None:
    custom_root = tmp_path / "cloud-data"
    monkeypatch.setenv("DATA_ROOT", str(custom_root))
    monkeypatch.delenv("RAW_DATA_DIR", raising=False)
    monkeypatch.delenv("PROCESSED_DATA_DIR", raising=False)

    assert data.get_data_root() == custom_root
    assert data.get_processed_dir() == custom_root / "processed"
    assert data.get_raw_dir() == custom_root / "raw"
