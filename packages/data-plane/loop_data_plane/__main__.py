"""S140: container entrypoint for the dp-runtime image.

Prints the package version (from importlib.metadata) and exits 0. The
real runtime loop will replace this once the data-plane process model
lands; until then the entrypoint must succeed so the distroless image
is exercise-able by the CI smoke and image-size budget.
"""

from __future__ import annotations

import sys
from importlib.metadata import PackageNotFoundError, version


def main() -> int:
    try:
        ver = version("loop-data-plane")
    except PackageNotFoundError:  # pragma: no cover — defensive only.
        ver = "unknown"
    sys.stdout.write(f"loop-data-plane {ver}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
