"""Thin wrapper around the Alembic CLI for the data plane."""

from __future__ import annotations

import sys
from importlib.resources import files
from pathlib import Path

from alembic.config import CommandLine, Config


def _ini_path() -> Path:
    return Path(str(files("loop_data_plane.migrations").joinpath("alembic.ini")))


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    cli = CommandLine()
    options = cli.parser.parse_args(args)
    if not hasattr(options, "cmd"):
        cli.parser.error("too few arguments")
    cfg = Config(file_=str(_ini_path()), ini_section="alembic", cmd_opts=options)
    cli.run_cmd(cfg, options)
    return 0
