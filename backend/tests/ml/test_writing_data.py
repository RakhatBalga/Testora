import json
from pathlib import Path

import pytest

from ml.writing_data import (
    prompt_group,
    Essay,
    assign_public_splits,
    build_dataset,
    build_manifest,
    deduplicate,
    load_calibration_bank,
    load_gold,
    load_public_csv,
    read_essays,
    verify_manifest,
    write_essays,
)
from writing_synth import make_essays

BANK = Path(__file__).resolve().parents[1] / "fixtures" / "writing_calibration_bank.jsonl"


def essay(id_, text, prompt="P", **kw):
    return Essay(id=id_, task_type=2, prompt=prompt, text=text, overall=6.0, source="t", **kw)


def test_schema_rejects_non_half_band_and_derives_hashes():
    with pytest.raises(ValueError):
        Essay(id="a", task_type=2, prompt="p", text="t", overall=6.3, source="x")
    e = essay("a", "Hello, World!")
    assert len(e.text_hash) == 64 and e.prompt_id
    assert essay("b", "hello world").text_hash == e.text_hash  # normalised


def test_bank_loader_is_dev_with_range_labels():
    essays = load_calibration_bank(BANK)
    assert len(essays) == 8
    assert {e.split for e in essays} == {"dev"}
    assert all(e.label_kind == "range" and e.label_min < e.label_max for e in essays)
    assert all(e.overall * 2 == round(e.overall * 2) for e in essays)


def test_public_csv_mapping_snapping_and_skips(tmp_path):
    csv = tmp_path / "p.csv"
    csv.write_text(
        "Task_Type,Question,Essay,Overall,Task_Response\n"
        "Task 2,Q one,Essay text one,6.8,6\n"
        "1,Q two,Essay text two,not-a-band,5\n"
        "2,Q three,,7,7\n",
        encoding="utf-8",
    )
    essays, skipped = load_public_csv(csv, source="pub", licence="cc")
    assert len(essays) == 1 and essays[0].overall == 7.0 and essays[0].criteria == {"task": 6.0}
    assert [s["reason"] for s in skipped] == ["no overall band", "empty text"]
    with pytest.raises(ValueError, match="missing mapped columns"):
        load_public_csv(csv, source="pub", licence="cc", column_map={"text": "Nope"})


def test_gold_loader_mean_adjudication_and_disagreement(tmp_path):
    def row(i, a, b, **extra):
        return json.dumps(
            {
                "id": i,
                "task_type": 2,
                "prompt": "p",
                "text": f"text {i}",
                "ratings": [{"rater_id": "T1", "overall": a}, {"rater_id": "T2", "overall": b}],
                **extra,
            }
        )

    path = tmp_path / "g.jsonl"
    path.write_text("\n".join([row("a", 6.0, 6.5), row("b", 5.0, 7.0, adjudicated={"overall": 6.0})]))
    a, b = load_gold(path)
    assert a.overall == 6.5 and a.label_kind == "exact" and a.raters == ["T1", "T2"] and a.split == "gold"
    assert b.overall == 6.0 and b.label_kind == "adjudicated"
    path.write_text(row("c", 5.0, 7.0))
    with pytest.raises(ValueError, match="adjudicate"):
        load_gold(path)


def test_dedup_exact_near_and_priority():
    base = " ".join(f"word{i}" for i in range(80))
    near = base + " extra tail words here"
    other = " ".join(f"different{i}" for i in range(80))
    kept, removed = deduplicate(
        [essay("gold1", base), essay("pub1", base.upper()), essay("pub2", near), essay("pub3", other)]
    )
    assert [e.id for e in kept] == ["gold1", "pub3"]
    assert {r["id"]: r["reason"] for r in removed} == {"pub1": "exact", "pub2": "near"}
    assert all(r["duplicate_of"] == "gold1" for r in removed)


def test_prompt_grouped_split_is_deterministic_and_leaves_dev_gold_alone():
    pool = make_essays(80, n_prompts=10)
    fixed = [
        e.model_copy(update={"split": "dev", "prompt": f"Dev prompt {i}", "prompt_id": prompt_group(f"Dev prompt {i}")})
        for i, e in enumerate(make_essays(3, prefix="d"))
    ]
    fixed += [
        e.model_copy(
            update={"split": "gold", "prompt": f"Gold prompt {i}", "prompt_id": prompt_group(f"Gold prompt {i}")}
        )
        for i, e in enumerate(make_essays(3, prefix="g"))
    ]
    first = assign_public_splits(pool + fixed, test_fraction=0.3, seed=7)
    again = assign_public_splits(pool + fixed, test_fraction=0.3, seed=7)
    assert [e.split for e in first] == [e.split for e in again]
    train = {e.prompt_id for e in first if e.split == "train"}
    test = {e.prompt_id for e in first if e.split == "test"}
    assert train and test and not train & test
    assert {e.split for e in first if e.id.startswith("d")} == {"dev"}
    assert {e.split for e in first if e.id.startswith("g")} == {"gold"}


def test_manifest_detects_tampering_and_leakage():
    essays = assign_public_splits(make_essays(60, n_prompts=10), seed=1)
    manifest = build_manifest(essays, [], seed=1, test_fraction=0.3)
    assert verify_manifest(essays, manifest) == []
    tampered = [e.model_copy(update={"overall": 9.0}) if i == 0 else e for i, e in enumerate(essays)]
    assert verify_manifest(tampered, manifest)
    train = next(e for e in essays if e.split == "train")
    leak = essays + [train.model_copy(update={"id": "copy", "split": "test"})]
    assert any(
        "also appear in train" in p for p in verify_manifest(leak, build_manifest(leak, [], seed=1, test_fraction=0.3))
    )


def test_build_dataset_end_to_end_and_overwrite_protection(tmp_path):
    out, manifest = tmp_path / "d.jsonl", tmp_path / "m.json"
    info = build_dataset(bank=BANK, public=[], gold=None, out=out, manifest=manifest)
    assert info["splits"]["dev"]["n"] == 8
    assert len(read_essays(out)) == 8
    with pytest.raises(FileExistsError):
        build_dataset(bank=BANK, public=[], gold=None, out=out, manifest=manifest)
    write_essays(out, read_essays(out), overwrite=True)
