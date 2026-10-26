"""Blob storage, avatars, Speaking submit API and its server-side gate, auth hardening."""
import io
import os

import pytest

from app.application import speaking as speaking_service
from app.domain.models.speaking import SpeakingSubmission, SpeakingTask
from app.domain.models.stored_file import StoredFile
from app.domain.models.user import User
from app.infrastructure import storage
from app.infrastructure.ai.base import Feedback, MistakeItem
from app.infrastructure.config import settings
from app.infrastructure.storage.sniff import sniff_audio, sniff_image
from app.domain.models.mistake import Mistake

WEBM = b"\x1a\x45\xdf\xa3" + b"\x00" * 64
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64


class _SpeakingGrader:
    seen_path = None

    def grade(self, *, part, questions, audio_path, transcript=None):
        type(self).seen_path = audio_path
        assert os.path.exists(audio_path)  # the grader gets a real file...
        return Feedback(band=6.5, criteria={"Fluency & Coherence": 6.5}, summary="ok",
                        mistakes=[MistakeItem(category="fluency", subskill="pauses", severity=2)])


@pytest.fixture()
def speaking_api(api, monkeypatch):
    monkeypatch.setattr(settings, "SPEAKING_ENABLED", True)
    monkeypatch.setattr(settings, "FREE_SPEAKING_SUBMISSIONS", 2)
    monkeypatch.setattr(speaking_service, "get_speaking_grader", lambda: _SpeakingGrader())
    with api.Session() as db:
        db.add(SpeakingTask(id=1, part=1, questions=["Where do you live?"]))
        db.commit()
    return api


def _submit(api, data=WEBM, name="a.webm"):
    return api.client.post("/speaking/submit", headers=api.headers, data={"task_id": "1"},
                           files={"audio": (name, io.BytesIO(data), "audio/webm")})


def test_sniffers_use_magic_bytes_not_names():
    assert sniff_image(PNG) == "image/png" and sniff_image(JPEG) == "image/jpeg"
    assert sniff_image(b"<html><script>alert(1)</script>") is None
    assert sniff_image(b"RIFF\x00\x00\x00\x00WEBPVP8 ") == "image/webp"
    assert sniff_audio(WEBM) == "audio/webm"
    assert sniff_audio(b"\x00\x00\x00\x20ftypM4A ") == "audio/mp4"
    assert sniff_audio(b"MZ\x90\x00 not audio") is None


def test_speaking_submit_stores_audio_in_database_and_streams_it_back(speaking_api):
    response = _submit(speaking_api)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["band"] == 6.5 and body["audio_url"].endswith(f"/{body['id']}/audio")
    with speaking_api.Session() as db:
        sub = db.get(SpeakingSubmission, body["id"])
        assert sub.audio_url.startswith("db:")
        assert db.get(StoredFile, sub.audio_url[3:]).data == WEBM
        assert db.query(Mistake).filter_by(skill="speaking").count() == 1
    assert not os.path.exists(_SpeakingGrader.seen_path)  # ...and the temp copy is cleaned up
    audio = speaking_api.client.get(body["audio_url"], headers=speaking_api.headers)
    assert audio.status_code == 200 and audio.content == WEBM
    assert audio.headers["content-type"] == "audio/webm"
    assert audio.headers["x-content-type-options"] == "nosniff"


def test_audio_is_private_to_its_owner(speaking_api):
    body = _submit(speaking_api).json()
    with speaking_api.Session() as db:
        other = User(username="other", password="x")
        db.add(other)
        db.commit()
        from app.infrastructure.security import create_access_token
        headers = {"Authorization": f"Bearer {create_access_token(other.id)}"}
    assert speaking_api.client.get(body["audio_url"], headers=headers).status_code == 404
    assert speaking_api.client.get(body["audio_url"]).status_code == 401


def test_speaking_rejects_non_audio_and_oversized_uploads(speaking_api, monkeypatch):
    assert _submit(speaking_api, data=b"MZ" + b"\x00" * 100, name="evil.webm").status_code == 415
    monkeypatch.setattr(settings, "MAX_AUDIO_UPLOAD_MB", 0)
    assert _submit(speaking_api).status_code == 413
    with speaking_api.Session() as db:
        assert db.query(SpeakingSubmission).count() == 0 and db.query(StoredFile).count() == 0


@pytest.mark.parametrize("flag, limit", [(False, 2), (True, 0)])
def test_speaking_submit_is_gated_server_side(speaking_api, monkeypatch, flag, limit):
    monkeypatch.setattr(settings, "SPEAKING_ENABLED", flag)
    monkeypatch.setattr(settings, "FREE_SPEAKING_SUBMISSIONS", limit)
    monkeypatch.setattr(speaking_service, "get_speaking_grader", lambda: pytest.fail("grader must not run"))
    response = _submit(speaking_api)
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "speaking_disabled"


def test_failed_speaking_grading_keeps_audio_but_no_band_and_hides_provider_text(speaking_api, monkeypatch):
    class Broken(_SpeakingGrader):
        def grade(self, **kwargs):
            return Feedback(band=0.0, criteria={}, summary="429 RESOURCE_EXHAUSTED project 123", error=True)

    monkeypatch.setattr(speaking_service, "get_speaking_grader", lambda: Broken())
    body = _submit(speaking_api).json()
    assert body["band"] is None and "RESOURCE_EXHAUSTED" not in str(body["feedback"])
    assert speaking_api.client.get("/speaking/quota", headers=speaking_api.headers).json()["used"] == 0


def test_avatar_is_validated_by_magic_bytes_and_served_with_nosniff(api):
    bad = api.client.post("/auth/me/avatar", headers=api.headers,
                          files={"image": ("me.png", io.BytesIO(b"<svg onload=alert(1)>"), "image/png")})
    assert bad.status_code == 400
    ok = api.client.post("/auth/me/avatar", headers=api.headers,
                         files={"image": ("anything.bin", io.BytesIO(PNG), "application/octet-stream")})
    assert ok.status_code == 200
    url = ok.json()["avatar"]
    assert url.startswith("/auth/avatars/")
    served = api.client.get(url)  # public: <img> tags cannot send a bearer token
    assert served.status_code == 200 and served.content == PNG
    assert served.headers["content-type"] == "image/png"
    assert served.headers["x-content-type-options"] == "nosniff"
    # Replacing the avatar deletes the old blob; deleting clears the user.
    api.client.post("/auth/me/avatar", headers=api.headers, files={"image": ("a.jpg", io.BytesIO(JPEG), "image/jpeg")})
    assert api.client.get(url).status_code == 404
    assert api.client.delete("/auth/me/avatar", headers=api.headers).json()["avatar"] is None
    with api.Session() as db:
        assert db.query(StoredFile).count() == 0


def test_avatar_over_the_cap_is_rejected(api, monkeypatch):
    monkeypatch.setattr(settings, "MAX_AVATAR_UPLOAD_MB", 0)
    response = api.client.post("/auth/me/avatar", headers=api.headers,
                               files={"image": ("a.png", io.BytesIO(PNG), "image/png")})
    assert response.status_code == 413


def test_local_storage_backend_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "PRIVATE_AUDIO_DIR", tmp_path / "audio")
    monkeypatch.setattr(storage, "AVATAR_DIR", tmp_path / "avatars")
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "local")
    backend = storage.get_storage()
    key = backend.save(None, kind="speaking_audio", owner_id=7, data=WEBM, content_type="audio/webm")
    assert not key.startswith("db:")
    blob = storage.storage_for_key(key).load(None, key)
    assert blob.data == WEBM and blob.content_type == "audio/webm"
    assert storage.storage_for_key("../../etc/passwd").load(None, "../../etc/passwd") is None
    backend.delete(None, key)
    assert backend.load(None, key) is None


# ---- auth hardening ---------------------------------------------------------

def test_password_limit_is_measured_in_bytes(api):
    cyrillic = "п" * 40  # 40 characters but 80 bytes: bcrypt would silently truncate it
    response = api.client.post("/auth/register", json={"username": "newuser", "password": cyrillic})
    assert response.status_code == 422
    assert "72 bytes" in response.text
    ok = api.client.post("/auth/register", json={"username": "newuser", "password": "п" * 36})
    assert ok.status_code == 200
    login = api.client.post("/auth/login", json={"username": "newuser", "password": "п" * 36})
    assert login.status_code == 200


def test_logout_revokes_existing_tokens(api):
    assert api.client.get("/auth/me", headers=api.headers).status_code == 200
    assert api.client.post("/auth/logout", headers=api.headers).status_code == 204
    assert api.client.get("/auth/me", headers=api.headers).status_code == 401


def test_unhandled_errors_return_a_generic_message_with_request_id(api, monkeypatch):
    from fastapi.testclient import TestClient
    from app.application import accounts
    from app.main import app

    monkeypatch.setattr(accounts, "update_profile", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("secret dsn")))
    response = TestClient(app, raise_server_exceptions=False).patch(
        "/auth/me", headers=api.headers, json={"native_language": "Russian"})
    assert response.status_code == 500
    assert "secret dsn" not in response.text and response.json()["request_id"]
