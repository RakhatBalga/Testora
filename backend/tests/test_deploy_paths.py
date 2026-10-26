from pathlib import Path

from fastapi.testclient import TestClient

from app.infrastructure import storage
from app.main import STATIC_DIR, app


def test_speaking_upload_dir_matches_backend_root_volume():
    backend_root = Path(storage.__file__).resolve().parents[3]

    assert storage.PRIVATE_AUDIO_DIR == backend_root / "private" / "audio_submissions"
    # Recordings are never served from the public /static mount.
    assert STATIC_DIR not in storage.PRIVATE_AUDIO_DIR.parents


def test_listening_audio_is_packaged_under_mounted_static_directory():
    audio = STATIC_DIR / "audio" / "listening" / "testora-studio-02.m4a"

    assert STATIC_DIR.name == "static"
    assert audio.is_file()


def test_listening_audio_supports_range_requests():
    response = TestClient(app).get(
        "/static/audio/listening/testora-studio-02.m4a",
        headers={"Range": "bytes=0-1023"},
    )

    assert response.status_code == 206
    assert response.headers["accept-ranges"] == "bytes"
    assert response.headers["content-range"].startswith("bytes 0-1023/")
    assert len(response.content) == 1024
