"""Read-only installation and path diagnostics."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .utils import is_within
from .zotero import ZoteroDatabase, ZoteroDatabaseError


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """One doctor check result."""

    level: str
    message: str


def run_diagnostics(
    *,
    zotero_data_dir: Path,
    database_path: Path | None = None,
    linked_attachment_base_dir: Path | None = None,
    output_root: Path | None = None,
    snapshot: bool = False,
) -> list[Diagnostic]:
    """Inspect configuration without modifying Zotero or an export workspace."""

    data_dir = zotero_data_dir.expanduser().resolve()
    database = (
        database_path.expanduser().resolve()
        if database_path
        else data_dir / "zotero.sqlite"
    )
    results: list[Diagnostic] = []
    results.append(
        Diagnostic("ok", f"Zotero data directory: {data_dir}")
        if data_dir.is_dir()
        else Diagnostic("error", f"Zotero data directory does not exist: {data_dir}")
    )
    results.append(
        Diagnostic("ok", f"Zotero database: {database}")
        if database.is_file()
        else Diagnostic("error", f"Zotero database does not exist: {database}")
    )

    if database.is_file():
        try:
            with ZoteroDatabase(
                data_dir,
                database_path=database,
                linked_attachment_base_dir=linked_attachment_base_dir,
                snapshot=snapshot,
            ) as zotero:
                query_only = int(zotero.connection.execute("PRAGMA query_only").fetchone()[0])
                collection_count = len(zotero.list_collections())
                if query_only != 1:
                    results.append(Diagnostic("error", "SQLite query-only protection is disabled"))
                else:
                    results.append(
                        Diagnostic(
                            "ok",
                            f"Read-only SQLite connection works; {collection_count} collections found",
                        )
                    )
        except ZoteroDatabaseError as exc:
            results.append(Diagnostic("error", str(exc)))

    storage = data_dir / "storage"
    results.append(
        Diagnostic("ok", f"Stored attachment directory: {storage}")
        if storage.is_dir()
        else Diagnostic("warning", f"Stored attachment directory not found: {storage}")
    )

    if linked_attachment_base_dir is not None:
        linked = linked_attachment_base_dir.expanduser().resolve()
        results.append(
            Diagnostic("ok", f"Linked attachment base directory: {linked}")
            if linked.is_dir()
            else Diagnostic("warning", f"Linked attachment base directory not found: {linked}")
        )

    if output_root is not None:
        output = output_root.expanduser().resolve()
        if is_within(output, data_dir):
            results.append(
                Diagnostic("error", f"Output directory is inside Zotero data: {output}")
            )
        else:
            existing_parent = output
            while not existing_parent.exists() and existing_parent != existing_parent.parent:
                existing_parent = existing_parent.parent
            if existing_parent.is_dir() and os.access(existing_parent, os.W_OK):
                results.append(Diagnostic("ok", f"Output directory is writable: {output}"))
            else:
                results.append(Diagnostic("error", f"Output directory is not writable: {output}"))
    return results
