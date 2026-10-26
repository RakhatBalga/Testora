"""Scored-essay dataset layer for E1 (Writing accuracy).

Schema `writing-essay.v1` (one JSON object per line, UTF-8 JSONL):

    id            unique string within the file
    task_type     1 or 2
    prompt        the exam question shown to the candidate
    text          the essay
    overall       human overall band, multiple of 0.5 in [0, 9]
    criteria      optional {"task","coherence","lexical","grammar"} -> band
                  (task = Task Response for Task 2, Task Achievement for Task 1)
    rater_scores  optional list of {"rater_id", "overall", "criteria"?} - every
                  human mark; used for the human-human ceiling row
    raters        rater ids (derived from rater_scores when empty)
    source        where the essay came from (required, never "")
    licence       reuse terms ("unknown" is allowed but is reported)
    split         dev | train | test | gold
    label_kind    exact | range | adjudicated (range = only a window is known;
                  overall is the window midpoint, label_min/label_max the window)
    prompt_id     group key for prompt-grouped splitting (hash of normalised prompt)
    text_hash     sha256 of the normalised text (cache key / dedup key)

Split semantics: `dev` = the 8-essay calibration bank, used while the prompt was
tuned, so it can NEVER be a test set; `train`/`test` = a public corpus split by
prompt group; `gold` = the double-marked teacher set.

Raw essays stay outside Git (see calibration/README.md).
"""
import argparse
import csv
import hashlib
import json
import random
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator

from ml.data import Record
from ml.metrics import half_band

SCHEMA_VERSION = "writing-essay.v1"
MANIFEST_VERSION = "writing-split-manifest.v1"
CRITERIA = ("task", "coherence", "lexical", "grammar")
SPLITS = ("dev", "train", "test", "gold")

# Display names used by app.infrastructure.ai.schemas -> canonical keys.
_CRITERION_ALIASES = (
    ("task", "task"), ("coherence", "coherence"), ("lexical", "lexical"),
    ("grammat", "grammar"),
)


def canonical_criterion(name: str) -> str | None:
    lowered = name.lower()
    for needle, key in _CRITERION_ALIASES:
        if needle in lowered:
            return key
    return None


def canonical_criteria(criteria: dict[str, float] | None) -> dict[str, float]:
    out: dict[str, float] = {}
    for name, value in (criteria or {}).items():
        key = canonical_criterion(name)
        if key is not None and value is not None:
            out[key] = value
    return out


def normalise_text(text: str) -> str:
    """Lowercase, alphanumerics only, single spaces. Used for hashes and dedup."""
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def text_hash(text: str) -> str:
    return hashlib.sha256(normalise_text(text).encode("utf-8")).hexdigest()


def prompt_group(prompt: str) -> str:
    return hashlib.sha256(normalise_text(prompt).encode("utf-8")).hexdigest()[:16]


def _band(value, label: str) -> float:
    value = float(value)
    if not 0 <= value <= 9 or value * 2 != round(value * 2):
        raise ValueError(f"{label} must be a half band in [0, 9], got {value}")
    return value


class RaterScore(Record):
    rater_id: str = Field(min_length=1)
    overall: float = Field(ge=0, le=9, multiple_of=0.5)
    criteria: dict[str, float] = Field(default_factory=dict)

    @field_validator("criteria")
    @classmethod
    def valid_criteria(cls, value):
        for key, band in value.items():
            if key not in CRITERIA:
                raise ValueError(f"unknown criterion {key!r}")
            _band(band, key)
        return value


class Essay(Record):
    schema_version: Literal["writing-essay.v1"] = SCHEMA_VERSION
    id: str = Field(min_length=1)
    task_type: Literal[1, 2]
    prompt: str = Field(min_length=1)
    text: str = Field(min_length=1)
    overall: float = Field(ge=0, le=9, multiple_of=0.5)
    criteria: dict[str, float] = Field(default_factory=dict)
    rater_scores: list[RaterScore] = Field(default_factory=list)
    raters: list[str] = Field(default_factory=list)
    source: str = Field(min_length=1)
    licence: str = "unknown"
    split: Literal["dev", "train", "test", "gold"] = "train"
    label_kind: Literal["exact", "range", "adjudicated"] = "exact"
    label_min: float | None = Field(default=None, ge=0, le=9)
    label_max: float | None = Field(default=None, ge=0, le=9)
    prompt_id: str = ""
    text_hash: str = ""
    notes: str | None = None

    @field_validator("id", "prompt", "text", "source")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value.strip()

    @field_validator("criteria")
    @classmethod
    def valid_criteria(cls, value):
        for key, band in value.items():
            if key not in CRITERIA:
                raise ValueError(f"unknown criterion {key!r}")
            _band(band, key)
        return value

    @model_validator(mode="after")
    def derive(self):
        if not self.prompt_id:
            self.prompt_id = prompt_group(self.prompt)
        if not self.text_hash:
            self.text_hash = text_hash(self.text)
        if not self.raters and self.rater_scores:
            self.raters = [r.rater_id for r in self.rater_scores]
        if self.label_kind == "range" and (self.label_min is None or self.label_max is None):
            raise ValueError("range labels need label_min and label_max")
        return self


# --------------------------------------------------------------------- IO

def read_essays(path: Path) -> list[Essay]:
    essays, seen = [], set()
    for number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            essay = Essay.model_validate_json(line)
        except ValueError as exc:
            # Never echo essay text in errors (may be private).
            raise ValueError(f"{path}:{number} is not a valid {SCHEMA_VERSION} record: "
                             f"{type(exc).__name__}") from None
        if essay.id in seen:
            raise ValueError(f"{path}:{number} duplicate id {essay.id!r}")
        seen.add(essay.id)
        essays.append(essay)
    return essays


def write_essays(path: Path, essays: list[Essay], *, overwrite: bool = False) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w" if overwrite else "x", encoding="utf-8") as handle:
        for essay in essays:
            handle.write(essay.model_dump_json() + "\n")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ---------------------------------------------------------------- loaders

def load_calibration_bank(path: Path, *, source: str = "calibration-bank (developer-chosen windows)",
                          licence: str = "private-dev-only") -> list[Essay]:
    """The existing 8-essay bank. Always `dev`, labels are windows, never exact."""
    essays = []
    for number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        row = json.loads(line)
        low, high = row.get("expected_min"), row.get("expected_max")
        band = row.get("expected_band")
        if band is not None:
            low = band if low is None else low
            high = band if high is None else high
        if low is None or high is None:
            raise ValueError(f"{path}:{number} has no expected band or window")
        kind = "exact" if low == high else "range"
        essays.append(Essay(
            id=str(row.get("id") or f"bank_{number:03d}"), task_type=int(row["task_type"]),
            prompt=row["prompt"], text=row["text"], overall=half_band((low + high) / 2),
            label_kind=kind, label_min=float(low), label_max=float(high),
            source=row.get("source") or source, licence=licence, split="dev",
            notes=row.get("notes")))
    return essays


# Column guess for the Kaggle "IELTS Writing Scored Essays Dataset"; VERIFY
# against the file you downloaded and override with --map if it differs.
KAGGLE_DEFAULT_MAP = {
    "task_type": "Task_Type", "prompt": "Question", "text": "Essay", "overall": "Overall",
    "task": "Task_Response", "coherence": "Coherence_Cohesion",
    "lexical": "Lexical_Resource", "grammar": "Range_Accuracy", "id": "",
}


def _parse_band(raw) -> float | None:
    if raw is None:
        return None
    raw = str(raw).strip()
    if not raw or raw.lower() in {"nan", "none", "null", "na", "n/a"}:
        return None
    match = re.search(r"\d+(?:\.\d+)?", raw)
    if not match:
        return None
    value = float(match.group())
    return half_band(value) if 0 <= value <= 9 else None


def _parse_task(raw) -> int | None:
    match = re.search(r"[12]", str(raw))
    return int(match.group()) if match else None


def load_public_csv(path: Path, *, source: str, licence: str, column_map: dict[str, str] | None = None,
                    id_prefix: str = "pub") -> tuple[list[Essay], list[dict]]:
    """Convert a public scored-essay CSV. Returns (essays, skipped_rows_with_reason).

    Rows are skipped, never guessed: missing text, prompt, task type or overall.
    Labels that are not half bands are snapped to the nearest half band. Public
    labels are normally a single non-certified rater, so rater_scores stays empty.
    """
    mapping = {**KAGGLE_DEFAULT_MAP, **(column_map or {})}
    essays, skipped = [], []
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing = [col for key, col in mapping.items()
                   if col and key in ("task_type", "prompt", "text", "overall")
                   and col not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"CSV is missing mapped columns {missing}; "
                             f"found {reader.fieldnames}. Pass --map key=Column.")
        for number, row in enumerate(reader, 2):
            def get(key):
                col = mapping.get(key)
                return row.get(col) if col else None
            task = _parse_task(get("task_type"))
            overall = _parse_band(get("overall"))
            text, prompt = (get("text") or "").strip(), (get("prompt") or "").strip()
            reason = ("no task type" if task is None else "no overall band" if overall is None
                      else "empty text" if not text else "empty prompt" if not prompt else None)
            if reason:
                skipped.append({"row": number, "reason": reason})
                continue
            criteria = {}
            for key in CRITERIA:
                band = _parse_band(get(key))
                if band is not None:
                    criteria[key] = band
            essays.append(Essay(
                id=(get("id") or f"{id_prefix}_{number:05d}"), task_type=task, prompt=prompt,
                text=text, overall=overall, criteria=criteria, source=source, licence=licence,
                split="train"))
    return essays, skipped


def load_gold(path: Path, *, source: str = "AITU double-marked gold set",
              licence: str = "consented-private") -> list[Essay]:
    """Double-marked gold set.

    Input JSONL rows: id, task_type, prompt, text, ratings=[{rater_id, overall,
    criteria?}, ...] (>= 2 raters), optional adjudicated={overall, criteria?}.
    The label is the adjudicated mark when given, else the mean of the raters
    rounded to a half band. Disagreements > 1.0 band without adjudication are
    rejected: the owner must adjudicate them first (docs/09).
    """
    essays = []
    for number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        row = json.loads(line)
        scores = [RaterScore.model_validate(r) for r in row["ratings"]]
        if len(scores) < 2 or len({s.rater_id for s in scores}) != len(scores):
            raise ValueError(f"{path}:{number} needs >= 2 distinct raters")
        spread = max(s.overall for s in scores) - min(s.overall for s in scores)
        adjudicated = row.get("adjudicated")
        if spread > 1.0 and not adjudicated:
            raise ValueError(f"{path}:{number} raters differ by {spread}; adjudicate first")
        if adjudicated:
            overall, kind = _band(adjudicated["overall"], "adjudicated overall"), "adjudicated"
            criteria = {k: _band(v, k) for k, v in adjudicated.get("criteria", {}).items()}
        else:
            overall, kind = half_band(sum(s.overall for s in scores) / len(scores)), "exact"
            criteria = {}
            for key in CRITERIA:
                vals = [s.criteria[key] for s in scores if key in s.criteria]
                if len(vals) == len(scores):
                    criteria[key] = half_band(sum(vals) / len(vals))
        essays.append(Essay(
            id=str(row["id"]), task_type=int(row["task_type"]), prompt=row["prompt"],
            text=row["text"], overall=overall, criteria=criteria, rater_scores=scores,
            source=row.get("source") or source, licence=row.get("licence") or licence,
            split="gold", label_kind=kind, notes=row.get("notes")))
    return essays


# ------------------------------------------------------------------ dedup

_SKETCH = 24          # bottom-k min-hash sketch size
_SHINGLE = 5          # word 5-grams
_MIN_SHARED = 6       # candidate pair if sketches share this many hashes


def _shingles(text: str) -> set[int]:
    words = normalise_text(text).split()
    if len(words) < _SHINGLE:
        return {int(hashlib.md5(" ".join(words).encode()).hexdigest()[:12], 16)}
    return {int(hashlib.md5(" ".join(words[i:i + _SHINGLE]).encode()).hexdigest()[:12], 16)
            for i in range(len(words) - _SHINGLE + 1)}


def deduplicate(essays: list[Essay], *, near_threshold: float = 0.8
                ) -> tuple[list[Essay], list[dict]]:
    """Drop exact (normalised-text hash) and near duplicates (5-gram Jaccard).

    The earlier essay in the list wins, so pass sources in priority order
    (gold first, then public, then the dev bank). Returns (kept, removed) where
    removed rows say which essay they duplicated and why.
    """
    kept: list[Essay] = []
    removed: list[dict] = []
    by_hash: dict[str, Essay] = {}
    shingles: dict[str, set[int]] = {}
    index: dict[int, list[str]] = defaultdict(list)
    for essay in essays:
        twin = by_hash.get(essay.text_hash)
        if twin is not None:
            removed.append({"id": essay.id, "duplicate_of": twin.id, "reason": "exact",
                            "jaccard": 1.0, "split": essay.split})
            continue
        sh = _shingles(essay.text)
        sketch = sorted(sh)[:_SKETCH]
        votes: Counter = Counter()
        for h in sketch:
            for other in index.get(h, ()):
                votes[other] += 1
        near = None
        for other, count in votes.most_common():
            if count < min(_MIN_SHARED, len(sketch)):
                break
            o = shingles[other]
            jac = len(sh & o) / len(sh | o)
            if jac >= near_threshold:
                near = (other, jac)
                break
        if near:
            removed.append({"id": essay.id, "duplicate_of": near[0], "reason": "near",
                            "jaccard": round(near[1], 4), "split": essay.split})
            continue
        kept.append(essay)
        by_hash[essay.text_hash] = essay
        shingles[essay.id] = sh
        for h in sketch:
            index[h].append(essay.id)
    return kept, removed


# ------------------------------------------------------------------ splits

def assign_public_splits(essays: list[Essay], *, test_fraction: float = 0.3, seed: int = 42
                         ) -> list[Essay]:
    """Prompt-grouped train/test split of the `train`/`test` pool.

    All essays that share a prompt land in the same split. Groups are shuffled
    with a fixed seed and the first ones fill the test share. `dev` and `gold`
    essays are never moved.
    """
    pool = [e for e in essays if e.split in ("train", "test")]
    groups: dict[str, list[Essay]] = defaultdict(list)
    for e in pool:
        groups[e.prompt_id].append(e)
    order = sorted(groups)
    random.Random(seed).shuffle(order)
    target = test_fraction * len(pool)
    moved = 0
    test_groups = set()
    for gid in order:
        if moved >= target:
            break
        test_groups.add(gid)
        moved += len(groups[gid])
    return [e.model_copy(update={"split": ("test" if e.prompt_id in test_groups else "train")})
            if e.split in ("train", "test") else e for e in essays]


def _split_fingerprint(essays: list[Essay]) -> str:
    rows = sorted(f"{e.id}:{e.text_hash}:{e.overall}" for e in essays)
    return hashlib.sha256("\n".join(rows).encode()).hexdigest()


def build_manifest(essays: list[Essay], removed: list[dict], *, seed: int, test_fraction: float,
                   dataset_sha256: str | None = None) -> dict:
    by_split = defaultdict(list)
    for e in essays:
        by_split[e.split].append(e)
    prompts = {s: {e.prompt_id for e in items} for s, items in by_split.items()}
    overlaps = {f"{a}&{b}": len(prompts[a] & prompts[b])
                for a in sorted(prompts) for b in sorted(prompts) if a < b and prompts[a] & prompts[b]}
    return {
        "schema_version": MANIFEST_VERSION, "essay_schema": SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "seed": seed, "test_fraction": test_fraction, "dataset_sha256": dataset_sha256,
        "splits": {s: {"n": len(items), "n_prompts": len(prompts[s]),
                       "fingerprint": _split_fingerprint(items),
                       "bands": dict(sorted(Counter(str(e.overall) for e in items).items())),
                       "tasks": dict(sorted(Counter(str(e.task_type) for e in items).items())),
                       "ids": sorted(e.id for e in items)}
                   for s, items in sorted(by_split.items())},
        "prompt_overlap_between_splits": overlaps,
        "licences": dict(sorted(Counter(e.licence for e in essays).items())),
        "removed_duplicates": removed,
    }


def verify_manifest(essays: list[Essay], manifest: dict) -> list[str]:
    """Return a list of problems (empty = the dataset still matches the manifest)."""
    problems = []
    by_split = defaultdict(list)
    for e in essays:
        by_split[e.split].append(e)
    for split, info in manifest["splits"].items():
        if _split_fingerprint(by_split.get(split, [])) != info["fingerprint"]:
            problems.append(f"split {split!r} differs from the manifest (essays or labels changed)")
    for split in by_split:
        if split not in manifest["splits"]:
            problems.append(f"split {split!r} is not in the manifest")
    test_ids = {e.id for e in by_split.get("test", [])} | {e.id for e in by_split.get("gold", [])}
    train_hash = {e.text_hash for e in by_split.get("train", []) + by_split.get("dev", [])}
    leaked = [e.id for e in by_split.get("test", []) + by_split.get("gold", []) if e.text_hash in train_hash]
    if leaked:
        problems.append(f"{len(leaked)} test/gold essays also appear in train/dev (text hash)")
    if test_ids & {e.id for e in by_split.get("dev", [])}:
        problems.append("dev ids appear in test/gold")
    return problems


# --------------------------------------------------------------------- CLI

def build_dataset(*, bank: Path | None, public: list[tuple[Path, str, str, dict]], gold: Path | None,
                  out: Path, manifest: Path, seed: int = 42, test_fraction: float = 0.3,
                  overwrite: bool = False) -> dict:
    """gold -> public -> bank priority; dedup; prompt-grouped split; write both files."""
    essays: list[Essay] = []
    skipped: list[dict] = []
    if gold:
        essays += load_gold(gold)
    for path, source, licence, cmap in public:
        loaded, bad = load_public_csv(path, source=source, licence=licence, column_map=cmap)
        essays += loaded
        skipped += [{**b, "file": str(path)} for b in bad]
    if bank:
        essays += load_calibration_bank(bank)
    if len({e.id for e in essays}) != len(essays):
        raise ValueError("essay ids collide across inputs; give each source a distinct id prefix")
    kept, removed = deduplicate(essays)
    kept = assign_public_splits(kept, test_fraction=test_fraction, seed=seed)
    write_essays(out, kept, overwrite=overwrite)
    info = build_manifest(kept, removed, seed=seed, test_fraction=test_fraction,
                          dataset_sha256=file_sha256(out))
    info["skipped_public_rows"] = skipped
    manifest = Path(manifest)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    with manifest.open("w" if overwrite else "x", encoding="utf-8") as handle:
        handle.write(json.dumps(info, indent=2, ensure_ascii=False) + "\n")
    return info


def _parse_map(pairs: list[str]) -> dict[str, str]:
    out = {}
    for pair in pairs or []:
        key, _, col = pair.partition("=")
        if key not in KAGGLE_DEFAULT_MAP:
            raise SystemExit(f"--map key must be one of {sorted(KAGGLE_DEFAULT_MAP)}")
        out[key] = col
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build the E1 essay dataset and split manifest.")
    parser.add_argument("--bank", type=Path, help="tests/fixtures/writing_calibration_bank.jsonl (-> dev)")
    parser.add_argument("--public-csv", type=Path, help="public IELTS scored-essay CSV (-> train/test)")
    parser.add_argument("--public-source", default="public IELTS scored essays CSV")
    parser.add_argument("--public-licence", default="unknown-verify")
    parser.add_argument("--map", action="append", default=[], metavar="KEY=COLUMN",
                        help="CSV column mapping override, e.g. --map prompt=Question")
    parser.add_argument("--gold", type=Path, help="double-marked gold JSONL (-> gold)")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--test-fraction", type=float, default=0.3)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    public = ([(args.public_csv, args.public_source, args.public_licence, _parse_map(args.map))]
              if args.public_csv else [])
    info = build_dataset(bank=args.bank, public=public, gold=args.gold, out=args.out,
                         manifest=args.manifest, seed=args.seed, test_fraction=args.test_fraction,
                         overwrite=args.overwrite)
    for split, s in info["splits"].items():
        print(f"{split:5s} n={s['n']:5d} prompts={s['n_prompts']:4d} fingerprint={s['fingerprint'][:12]}")
    print(f"removed duplicates: {len(info['removed_duplicates'])}; "
          f"skipped public rows: {len(info['skipped_public_rows'])}")


if __name__ == "__main__":
    main()
