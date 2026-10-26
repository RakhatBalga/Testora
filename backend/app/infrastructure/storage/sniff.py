"""Detect file types from magic bytes (never trust extensions or client MIME)."""


def sniff_image(head: bytes) -> str | None:
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    return None


def sniff_audio(head: bytes) -> str | None:
    if head.startswith(b"\x1a\x45\xdf\xa3"):
        return "audio/webm"  # EBML: WebM/Matroska
    if head.startswith(b"OggS"):
        return "audio/ogg"
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return "audio/wav"
    if head.startswith(b"fLaC"):
        return "audio/flac"
    if head[4:8] == b"ftyp":
        return "audio/mp4"
    if head.startswith(b"ID3") or (len(head) > 1 and head[0] == 0xFF and head[1] & 0xE0 == 0xE0):
        # MPEG audio frame sync (mp3) or ADTS AAC (0xFFF1/0xFFF9)
        return "audio/aac" if len(head) > 1 and head[1] & 0xF6 == 0xF0 else "audio/mpeg"
    return None
