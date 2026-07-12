"""Small cross-cutting helpers."""

from __future__ import annotations

import logging
import os
import tempfile
from hashlib import sha256
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


def sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    """Return the SHA-256 digest of a file without loading it into memory."""

    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_text(path: Path, content: str) -> None:
    """Atomically replace a UTF-8 text file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
        temporary_path.replace(path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise
