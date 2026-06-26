from pathlib import Path

from app.api.routers import speaking


def test_speaking_upload_dir_matches_backend_root_volume():
    backend_root = Path(speaking.__file__).resolve().parents[3]

    assert speaking.UPLOAD_DIR == backend_root / "private" / "audio_submissions"
    assert speaking._LEGACY_DIR == backend_root / "static" / "audio_submissions"
