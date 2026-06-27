from pathlib import Path

from app.api.routers import speaking
from app.main import STATIC_DIR


def test_speaking_upload_dir_matches_backend_root_volume():
    backend_root = Path(speaking.__file__).resolve().parents[3]

    assert speaking.UPLOAD_DIR == backend_root / "private" / "audio_submissions"
    assert speaking._LEGACY_DIR == backend_root / "static" / "audio_submissions"


def test_listening_audio_is_packaged_under_mounted_static_directory():
    audio = STATIC_DIR / "audio" / "listening" / "test-01-section-1.m4a"

    assert STATIC_DIR.name == "static"
    assert audio.is_file()
