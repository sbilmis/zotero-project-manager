"""Small cross-cutting helpers."""

from __future__ import annotations

import logging
from pathlib import Path


def configure_logging(verbose: bool) -> None:
    """Configure application logging for a CLI invocation."""

    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
        force=True,
    )


def is_within(path: Path, parent: Path) -> bool:
    """Return whether *path* is equal to or contained by *parent*."""

    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True
