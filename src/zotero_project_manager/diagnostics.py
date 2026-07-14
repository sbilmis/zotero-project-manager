"""Read-only installation, runtime, database, and path diagnostics."""

from __future__ import annotations

import configparser
import os
import platform
import shutil
import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from . import __version__
from .utils import is_within
from .zotero import ZoteroDatabase, ZoteroDatabaseError


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """One stable doctor check result."""

    level: str
    message: str
    code: str = "general"


@dataclass(frozen=True, slots=True)
class ZoteroApplication:
    """A detected Zotero desktop application installation."""

    version: str
    build_id: str | None
    application_ini: Path


def find_zotero_application() -> ZoteroApplication | None:
    """Return the first recognizable Zotero desktop installation."""

    for path in _application_ini_candidates():
        if not path.is_file():
            continue
        parser = configparser.ConfigParser()
        try:
            parser.read(path, encoding="utf-8")
            if parser.get("App", "Name", fallback="").casefold() != "zotero":
                continue
            version = parser.get("App", "Version")
        except (configparser.Error, KeyError, OSError, ValueError):
            continue
        return ZoteroApplication(
            version=version,
            build_id=parser.get("App", "BuildID", fallback=None),
            application_ini=path,
        )
    return None


def is_zotero_running() -> bool | None:
    """Return whether Zotero is running, or ``None`` when detection is unavailable."""

    try:
        if os.name == "nt":
            completed = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq zotero.exe", "/FO", "CSV", "/NH"],
                check=False,
                capture_output=True,
                text=True,
                timeout=2,
            )
            return completed.returncode == 0 and "zotero.exe" in completed.stdout.casefold()
        executable = shutil.which("pgrep")
        if executable is None:
            return None
        for process_name in ("zotero", "Zotero"):
            completed = subprocess.run(
                [executable, "-x", process_name],
                check=False,
                capture_output=True,
                timeout=2,
            )
            if completed.returncode == 0:
                return True
        return False
    except (OSError, subprocess.SubprocessError):
        return None


def run_diagnostics(
    *,
    zotero_data_dir: Path,
    database_path: Path | None = None,
    linked_attachment_base_dir: Path | None = None,
    output_root: Path | None = None,
    config_path: Path | None = None,
    snapshot: bool = False,
    detect_runtime: bool = True,
) -> list[Diagnostic]:
    """Inspect zpm and Zotero readiness without modifying either data source."""

    data_dir = zotero_data_dir.expanduser().resolve()
    database = (
        database_path.expanduser().resolve()
        if database_path
        else data_dir / "zotero.sqlite"
    )
    results: list[Diagnostic] = [
        Diagnostic(
            "ok",
            f"zpm {__version__} using Python {platform.python_version()} at {sys.executable}",
            "zpm.runtime",
        )
    ]

    application = find_zotero_application()
    if application is None:
        results.append(
            Diagnostic("warning", "Zotero desktop application was not detected", "zotero.app")
        )
    else:
        build = f" (build {application.build_id})" if application.build_id else ""
        results.append(
            Diagnostic(
                "ok",
                f"Zotero {application.version}{build}: {application.application_ini}",
                "zotero.app",
            )
        )

    if detect_runtime:
        running = is_zotero_running()
        if running is True:
            results.append(
                Diagnostic(
                    "warning",
                    "Zotero is running. Direct SQLite exports may be temporarily locked; "
                    "the companion plugin avoids this by using Zotero's in-process read APIs.",
                    "zotero.process",
                )
            )
        elif running is False:
            results.append(Diagnostic("ok", "Zotero is not running", "zotero.process"))
        else:
            results.append(
                Diagnostic(
                    "warning",
                    "Could not determine whether Zotero is running",
                    "zotero.process",
                )
            )

    results.append(
        Diagnostic("ok", f"Zotero data directory: {data_dir}", "zotero.data_dir")
        if data_dir.is_dir()
        else Diagnostic(
            "error",
            f"Zotero data directory does not exist: {data_dir}",
            "zotero.data_dir",
        )
    )
    results.append(
        Diagnostic("ok", f"Zotero database: {database}", "zotero.database")
        if database.is_file()
        else Diagnostic(
            "error",
            f"Zotero database does not exist: {database}",
            "zotero.database",
        )
    )

    if database.is_file():
        try:
            with ZoteroDatabase(
                data_dir,
                database_path=database,
                linked_attachment_base_dir=linked_attachment_base_dir,
                snapshot=snapshot,
                snapshot_timeout=5,
            ) as zotero:
                query_only = int(zotero.connection.execute("PRAGMA query_only").fetchone()[0])
                collection_count = len(zotero.list_collections())
                if query_only != 1:
                    results.append(
                        Diagnostic(
                            "error",
                            "SQLite query-only protection is disabled",
                            "sqlite.read_only",
                        )
                    )
                else:
                    results.append(
                        Diagnostic(
                            "ok",
                            f"Read-only SQLite connection works; {collection_count} collections found",
                            "sqlite.read_only",
                        )
                    )
                results.extend(_attachment_diagnostics(zotero))
        except ZoteroDatabaseError as exc:
            results.append(Diagnostic("error", str(exc), "sqlite.read_only"))

    storage = data_dir / "storage"
    results.append(
        Diagnostic("ok", f"Stored attachment directory: {storage}", "zotero.storage")
        if storage.is_dir()
        else Diagnostic(
            "warning",
            f"Stored attachment directory not found: {storage}",
            "zotero.storage",
        )
    )

    if linked_attachment_base_dir is not None:
        linked = linked_attachment_base_dir.expanduser().resolve()
        results.append(
            Diagnostic(
                "ok", f"Linked attachment base directory: {linked}", "zotero.linked_dir"
            )
            if linked.is_dir()
            else Diagnostic(
                "warning",
                f"Linked attachment base directory not found: {linked}",
                "zotero.linked_dir",
            )
        )

    if config_path is not None:
        config = config_path.expanduser().resolve()
        results.append(
            Diagnostic(
                "ok" if config.is_file() else "warning",
                f"Configuration {'file' if config.is_file() else 'will be created'}: {config}",
                "zpm.config",
            )
        )

    if output_root is not None:
        results.append(_output_diagnostic(output_root.expanduser().resolve(), data_dir))
    else:
        results.append(
            Diagnostic(
                "warning",
                "No default output directory is configured; pass --output or run zpm config set",
                "zpm.output",
            )
        )
    return results


def _application_ini_candidates() -> tuple[Path, ...]:
    home = Path.home()
    candidates = [
        Path("/Applications/Zotero.app/Contents/Resources/app/application.ini"),
        home / "Applications/Zotero.app/Contents/Resources/app/application.ini",
        Path("/usr/lib/zotero/application.ini"),
        Path("/usr/lib/zotero/app/application.ini"),
        Path("/opt/zotero/application.ini"),
    ]
    for variable in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        root = os.environ.get(variable)
        if root:
            candidates.append(Path(root) / "Zotero" / "application.ini")
    return tuple(candidates)


def _attachment_diagnostics(zotero: ZoteroDatabase) -> list[Diagnostic]:
    try:
        rows = zotero.connection.execute(
            """
            SELECT items.key, itemAttachments.path
            FROM itemAttachments
            JOIN items ON items.itemID = itemAttachments.itemID
            WHERE itemAttachments.path IS NOT NULL
            """
        ).fetchall()
    except sqlite3.Error:
        return [
            Diagnostic(
                "warning",
                "Attachment inventory is unavailable for this Zotero schema",
                "zotero.attachments",
            )
        ]

    resolvable = 0
    missing = 0
    unresolved = 0
    for row in rows:
        source = zotero.resolve_attachment_path(str(row["path"]), str(row["key"]))
        if source is None:
            unresolved += 1
        elif source.is_file():
            resolvable += 1
        else:
            missing += 1
    level = "warning" if missing or unresolved else "ok"
    return [
        Diagnostic(
            level,
            f"Attachments: {len(rows)} recorded, {resolvable} available, "
            f"{missing} missing, {unresolved} unresolved linked paths",
            "zotero.attachments",
        )
    ]


def _output_diagnostic(output: Path, data_dir: Path) -> Diagnostic:
    if is_within(output, data_dir):
        return Diagnostic(
            "error", f"Output directory is inside Zotero data: {output}", "zpm.output"
        )
    existing_parent = output
    while not existing_parent.exists() and existing_parent != existing_parent.parent:
        existing_parent = existing_parent.parent
    if existing_parent.is_dir() and os.access(existing_parent, os.W_OK):
        return Diagnostic("ok", f"Output directory is writable: {output}", "zpm.output")
    return Diagnostic(
        "error", f"Output directory is not writable: {output}", "zpm.output"
    )
