"""Shared helper for size-capped multipart uploads."""
from fastapi import HTTPException, UploadFile, status

_CHUNK = 512 * 1024


def read_capped(upload: UploadFile, max_mb: int, label: str) -> bytes:
    """Read an upload fully but stop (413) as soon as it exceeds the cap."""
    limit = max_mb * 1024 * 1024
    chunks: list[bytes] = []
    total = 0
    while chunk := upload.file.read(_CHUNK):
        total += len(chunk)
        if total > limit:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"{label} exceeds the {max_mb} MB limit.",
            )
        chunks.append(chunk)
    if total == 0:
        raise HTTPException(status_code=400, detail=f"Empty {label.lower()} upload.")
    return b"".join(chunks)
