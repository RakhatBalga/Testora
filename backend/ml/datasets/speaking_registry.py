"""Compatibility entry point; use ml.datasets.speaking.registry."""

from ml.datasets.speaking.registry import (
    CRITERIA as CRITERIA,
    IDENTITY_COLUMNS as IDENTITY_COLUMNS,
    LABEL_COLUMNS as LABEL_COLUMNS,
    Code as Code,
    Recording as Recording,
    inspect_recordings as inspect_recordings,
    worksheet as worksheet,
    main as main,
)

if __name__ == "__main__":
    raise SystemExit(main())
