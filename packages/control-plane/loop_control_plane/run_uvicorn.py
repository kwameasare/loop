from __future__ import annotations

import os

import uvicorn


def _worker_count() -> int:
    raw = os.environ.get("UVICORN_WORKERS", "4")
    try:
        workers = int(raw)
    except ValueError:
        return 4
    return max(1, workers)


def main() -> None:
    uvicorn.run(
        "loop_control_plane.app:app",
        host="0.0.0.0",
        port=8080,
        workers=_worker_count(),
    )


if __name__ == "__main__":
    main()
