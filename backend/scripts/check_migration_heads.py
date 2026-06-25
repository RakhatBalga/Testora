"""Fail if the Alembic migration graph has more than one head.

Multiple heads mean two migrations share a parent (typically from merged
branches) and `alembic upgrade head` becomes ambiguous — a classic way to break
a deploy. Run in CI; exits non-zero when >1 head exists.

Reads the migration scripts directly (ScriptDirectory), so it needs neither a
database connection nor app settings/env vars.
"""
import sys
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND_DIR = Path(__file__).resolve().parents[1]


def main() -> int:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    if len(heads) > 1:
        print(f"ERROR: multiple Alembic heads detected: {heads}", file=sys.stderr)
        print("Create a merge migration: `alembic merge -m 'merge heads' <rev1> <rev2>`", file=sys.stderr)
        return 1
    print(f"OK: single Alembic head ({heads[0] if heads else 'none'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
