"""Shared, fail-closed visibility policy for practice content."""


def is_published(test) -> bool:
    metadata = test.content_metadata
    return (
        test.test_type in {"reading", "listening"}
        and isinstance(metadata, dict)
        and metadata.get("published") is True
        and not metadata.get("superseded_by")
    )
