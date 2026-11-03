"""Compatibility entry point; use ml.datasets.speaking.labels."""

from ml.datasets.speaking.labels import (
    ExpertRating as ExpertRating,
    import_ratings as import_ratings,
    assemble as assemble,
    build_bundle as build_bundle,
    main as main,
)

if __name__ == "__main__":
    raise SystemExit(main())
