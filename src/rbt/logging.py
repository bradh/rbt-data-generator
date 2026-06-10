"""Structured logging for the CLI.

Wraps :mod:`logging` with :class:`rich.logging.RichHandler` so that:

- TTYs get colored output matching ``scripts/lib/logging.sh``.
- Non-TTYs (CI, Docker logs, files) emit plain timestamps.
- Each invocation can optionally duplicate to a rotating file.
"""

from __future__ import annotations

import atexit
import logging
from pathlib import Path
from typing import Final

from rich.console import Console
from rich.logging import RichHandler

_LEVEL_MAP: Final[dict[str, int]] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARN": logging.WARNING,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def configure_logging(
    level: str = "INFO",
    *,
    log_file: Path | None = None,
    console: Console | None = None,
) -> logging.Logger:
    """Install a :class:`RichHandler` on the root logger and return ``rbt``'s logger."""
    root = logging.getLogger()
    root.setLevel(_LEVEL_MAP.get(level.upper(), logging.INFO))

    for handler in list(root.handlers):
        root.removeHandler(handler)

    rich_handler = RichHandler(
        console=console or Console(stderr=True),
        rich_tracebacks=True,
        show_time=True,
        show_level=True,
        show_path=False,
        markup=False,
    )
    rich_handler.setFormatter(logging.Formatter("%(message)s", datefmt="%H:%M:%S"))
    root.addHandler(rich_handler)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8", delay=True)
        file_handler.setFormatter(
            logging.Formatter(
                fmt="[%(asctime)s] [%(process)d] [%(levelname)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        root.addHandler(file_handler)
        atexit.register(file_handler.close)

    return logging.getLogger("rbt")


def get_logger(name: str = "rbt") -> logging.Logger:
    return logging.getLogger(name)


__all__ = ["configure_logging", "get_logger"]
