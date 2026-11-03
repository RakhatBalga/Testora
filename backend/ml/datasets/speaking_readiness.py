"""Compatibility entry point; use ml.datasets.speaking.readiness."""

from ml.datasets.speaking.readiness import (
    assess as assess,
    main as main,
)

if __name__ == "__main__":
    raise SystemExit(main())
