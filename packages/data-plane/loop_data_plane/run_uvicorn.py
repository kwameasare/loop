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
    # Binds to all interfaces because the process runs inside a
    # container; the kubernetes Service / ingress is the actual
    # network boundary. Locking to 127.0.0.1 here would make the
    # container unreachable from outside its network namespace.
    uvicorn.run(
        "loop_data_plane.runtime_app:app",
        host="0.0.0.0",  # noqa: S104
        port=8081,
        workers=_worker_count(),
    )


if __name__ == "__main__":
    main()
