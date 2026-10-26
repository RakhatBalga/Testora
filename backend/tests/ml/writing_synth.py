"""Synthetic essays for the E1 Writing tooling tests (no network, no paid calls)."""

import random

from ml.writing_data import Essay

_GOOD = (
    "however moreover consequently furthermore nevertheless government education technology "
    "society environment economic significant argue evidence perspective beneficial"
).split()
_BASIC = "good bad very thing big nice get lot people like".split()


def make_text(band: float, rng: random.Random) -> str:
    """Higher band -> longer, richer, better-punctuated text (a learnable signal)."""
    n_sent = int(6 + band * 2)
    sentences = []
    for _ in range(n_sent):
        pool = _GOOD if rng.random() < (band - 3) / 7 else _BASIC
        words = [rng.choice(pool) for _ in range(int(6 + band))]
        sentences.append(" ".join(words).capitalize() + ".")
    return "\n\n".join(" ".join(sentences[i : i + 4]) for i in range(0, len(sentences), 4))


def make_essays(n=60, n_prompts=12, seed=1, split="train", prefix="s", with_criteria=False):
    rng = random.Random(seed)
    out = []
    for i in range(n):
        band = rng.choice([4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0])
        crit = {"task": band, "coherence": band, "lexical": band, "grammar": band} if with_criteria else {}
        out.append(
            Essay(
                id=f"{prefix}{i:03d}",
                task_type=2,
                prompt=f"Prompt number {i % n_prompts} about topic.",
                text=make_text(band, rng) + f" Unique tag {prefix}{i}.",
                overall=band,
                criteria=crit,
                source="synthetic",
                licence="test",
                split=split,
            )
        )
    return out
