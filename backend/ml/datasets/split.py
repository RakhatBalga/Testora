"""Shared first-response temporal split for readiness checks and experiments."""
from ml.data import ResponseRecord


def first_responses(records: list[ResponseRecord]) -> list[ResponseRecord]:
    unique, seen = [], set()
    for row in sorted(records, key=lambda r: (r.answered_at, r.response_id)):
        key = (row.learner_id, row.item_key)
        if key not in seen:
            unique.append(row)
            seen.add(key)
    return unique


def temporal_split(records: list[ResponseRecord], train_fraction: float):
    if not 0 < train_fraction < 1:
        raise ValueError("train_fraction must be inside (0, 1)")
    if len({r.response_id for r in records}) != len(records):
        raise ValueError("Duplicate response IDs")
    unique = first_responses(records)
    if len(unique) < 4:
        raise ValueError("At least four first responses required")
    cutoff = unique[min(len(unique) - 1, max(1, int(len(unique) * train_fraction)))].answered_at
    train = [r for r in unique if r.answered_at < cutoff]
    test = [r for r in unique if r.answered_at >= cutoff]
    if not train or not test:
        raise ValueError("Need distinct timestamps on both sides of the split")
    return train, test, cutoff
