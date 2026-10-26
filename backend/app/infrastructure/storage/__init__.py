"""Blob storage for user uploads (avatars, speaking recordings).

`database` (default) keeps bytes in Postgres so they survive restarts on hosts
with an ephemeral disk (Render). `local` writes to disk for development. A key
returned by `save` is self-describing ("db:<id>" or a bare filename), so reads
keep working for whichever backend wrote the blob.
"""
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from sqlalchemy.orm import Session

from app.domain.models.stored_file import StoredFile
from app.infrastructure.config import settings

BACKEND_ROOT = Path(__file__).resolve().parents[3]
PRIVATE_AUDIO_DIR = BACKEND_ROOT / "private" / "audio_submissions"
AVATAR_DIR = BACKEND_ROOT / "static" / "avatars"
DB_PREFIX = "db:"

_AVATAR_EXT = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}
_AUDIO_EXT = {"audio/webm": ".webm", "audio/ogg": ".ogg", "audio/mpeg": ".mp3", "audio/wav": ".wav",
              "audio/mp4": ".m4a", "audio/aac": ".aac", "audio/flac": ".flac"}


@dataclass
class Blob:
    data: bytes
    content_type: str


class BlobStorage(Protocol):
    def save(self, db: Session, *, kind: str, owner_id: int, data: bytes, content_type: str) -> str: ...
    def load(self, db: Session, key: str) -> Blob | None: ...
    def delete(self, db: Session, key: str) -> None: ...


class DatabaseStorage:
    def save(self, db, *, kind, owner_id, data, content_type):
        blob_id = uuid.uuid4().hex
        db.add(StoredFile(id=blob_id, owner_id=owner_id, kind=kind, content_type=content_type,
                          size=len(data), data=data))
        db.flush()
        return DB_PREFIX + blob_id

    def load(self, db, key):
        if not key.startswith(DB_PREFIX):
            return None
        row = db.get(StoredFile, key[len(DB_PREFIX):])
        return Blob(bytes(row.data), row.content_type) if row else None

    def delete(self, db, key):
        if key.startswith(DB_PREFIX):
            row = db.get(StoredFile, key[len(DB_PREFIX):])
            if row is not None:
                db.delete(row)


class LocalDiskStorage:
    """Development backend. Files live under a private dir (audio) or static (avatars)."""

    @staticmethod
    def _dir(kind: str) -> Path:
        return AVATAR_DIR if kind == "avatar" else PRIVATE_AUDIO_DIR

    def save(self, db, *, kind, owner_id, data, content_type):
        ext = (_AVATAR_EXT if kind == "avatar" else _AUDIO_EXT).get(content_type, ".bin")
        directory = self._dir(kind)
        directory.mkdir(parents=True, exist_ok=True)
        name = f"{kind}_{owner_id}_{uuid.uuid4().hex}{ext}"
        (directory / name).write_bytes(data)
        return name

    def load(self, db, key):
        if key.startswith(DB_PREFIX):
            return None
        name = Path(key).name  # no path traversal
        for directory in (PRIVATE_AUDIO_DIR, AVATAR_DIR):
            path = directory / name
            if path.is_file():
                reverse = {v: k for d in (_AVATAR_EXT, _AUDIO_EXT) for k, v in d.items()}
                return Blob(path.read_bytes(), reverse.get(path.suffix, "application/octet-stream"))
        return None

    def delete(self, db, key):
        if key.startswith(DB_PREFIX):
            return
        name = Path(key).name
        for directory in (PRIVATE_AUDIO_DIR, AVATAR_DIR):
            try:
                (directory / name).unlink(missing_ok=True)
            except OSError:
                pass


def get_storage() -> BlobStorage:
    return LocalDiskStorage() if settings.STORAGE_BACKEND.lower() == "local" else DatabaseStorage()


def storage_for_key(key: str) -> BlobStorage:
    """Pick the backend that owns an existing key, regardless of current settings."""
    return DatabaseStorage() if key.startswith(DB_PREFIX) else LocalDiskStorage()
