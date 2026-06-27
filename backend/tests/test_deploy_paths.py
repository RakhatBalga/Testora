from pathlib import Path

from fastapi.testclient import TestClient

from app.api.routers import speaking
from app.main import STATIC_DIR, app


def test_speaking_upload_dir_matches_backend_root_volume():
    backend_root = Path(speaking.__file__).resolve().parents[3]

    assert speaking.UPLOAD_DIR == backend_root / "private" / "audio_submissions"
    assert speaking._LEGACY_DIR == backend_root / "static" / "audio_submissions"


def test_listening_audio_is_packaged_under_mounted_static_directory():
    audio = STATIC_DIR / "audio" / "listening" / "testora-studio-01.m4a"

    assert STATIC_DIR.name == "static"
    assert audio.is_file()


def test_listening_audio_supports_range_requests():
    response = TestClient(app).get(
        "/static/audio/listening/testora-studio-01.m4a",
        headers={"Range": "bytes=0-1023"},
    )

    assert response.status_code == 206
    assert response.headers["accept-ranges"] == "bytes"
    assert response.headers["content-range"].startswith("bytes 0-1023/")
    assert len(response.content) == 1024
