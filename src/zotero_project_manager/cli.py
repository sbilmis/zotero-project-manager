"""Typer command-line interface for Zotero Project Manager."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from . import __version__
from .collections import (
    CollectionError,
    build_collection_forest,
    format_collection_forest,
    resolve_collection,
)
from .diagnostics import run_diagnostics
from .exporter import CollectionExporter, ExportError
from .models import ExportStats
from .utils import configure_logging
from .zotero import ZoteroDatabase, ZoteroDatabaseError, default_zotero_data_dir

app = typer.Typer(
    name="zpm",
    help="Create clean, read-only-derived project workspaces from Zotero collections.",
    no_args_is_help=True,
    add_completion=False,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"zpm {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option("--version", callback=_version_callback, is_eager=True, help="Show the version."),
    ] = False,
) -> None:
    """Run Zotero Project Manager."""


def _data_dir(zotero_dir: Path | None, database: Path | None) -> Path:
    if zotero_dir is not None:
        return zotero_dir.expanduser()
    if database is not None:
        return database.expanduser().parent
    return default_zotero_data_dir()


def _print_stats(stats: list[ExportStats], *, show_changes: bool = False) -> None:
    for result in stats:
        if show_changes:
            for change in result.changes:
                detail = f" ({change.detail})" if change.detail else ""
                typer.echo(f"{change.action.upper():10} {change.destination}{detail}")
        typer.echo(
            f"{result.collection_name}: {result.copied} new, {result.updated} changed, "
            f"{result.unchanged} unchanged, {result.missing} missing, "
            f"{result.removed} removed, {result.pruned} pruned, "
            f"{result.protected} protected, {result.reconciled} reconciled "
            f"-> {result.workspace}"
        )


@app.command("list")
def list_collections(
    zotero_dir: Annotated[
        Path | None,
        typer.Option("--zotero-dir", help="Zotero data directory (default: auto-detect)."),
    ] = None,
    database: Annotated[
        Path | None,
        typer.Option("--database", help="Explicit path to zotero.sqlite."),
    ] = None,
    snapshot: Annotated[
        bool,
        typer.Option("--snapshot", help="Query a temporary SQLite snapshot instead of the live file."),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable diagnostic logging."),
    ] = False,
) -> None:
    """List the Zotero collection hierarchy and collection keys."""

    configure_logging(verbose)
    try:
        with ZoteroDatabase(
            _data_dir(zotero_dir, database), database_path=database, snapshot=snapshot
        ) as zotero:
            forest = build_collection_forest(zotero.list_collections())
            typer.echo(format_collection_forest(forest))
    except (ZoteroDatabaseError, CollectionError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


@app.command()
def export(
    collections: Annotated[
        list[str],
        typer.Argument(help="One or more collection names or collection keys."),
    ],
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Parent directory for exported workspaces."),
    ] = Path.cwd(),
    recursive: Annotated[
        bool,
        typer.Option("--recursive/--no-recursive", help="Include descendant collections."),
    ] = True,
    overwrite: Annotated[
        bool,
        typer.Option(
            "--overwrite",
            help="Adopt unmanaged destination directories and replace conflicting files.",
        ),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Report actions without writing any files."),
    ] = False,
    prune: Annotated[
        bool,
        typer.Option(
            "--prune",
            help="Delete removed manifest-owned files only when their SHA-256 still matches.",
        ),
    ] = False,
    verify: Annotated[
        bool,
        typer.Option("--verify", help="Recompute SHA-256 hashes even when timestamps match."),
    ] = False,
    pdf_only: Annotated[
        bool,
        typer.Option(
            "--pdf-only/--include-non-pdf",
            help="Export only PDFs or include every local attachment type.",
        ),
    ] = True,
    zotero_dir: Annotated[
        Path | None,
        typer.Option("--zotero-dir", help="Zotero data directory (default: auto-detect)."),
    ] = None,
    database: Annotated[
        Path | None,
        typer.Option("--database", help="Explicit path to zotero.sqlite."),
    ] = None,
    linked_attachment_base_dir: Annotated[
        Path | None,
        typer.Option(
            "--linked-attachment-base-dir",
            help="Base directory for Zotero paths beginning with 'attachments:'.",
        ),
    ] = None,
    snapshot: Annotated[
        bool,
        typer.Option("--snapshot", help="Query a temporary SQLite snapshot instead of the live file."),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable diagnostic logging."),
    ] = False,
) -> None:
    """Export one or more Zotero collections into project workspaces."""

    configure_logging(verbose)
    try:
        with ZoteroDatabase(
            _data_dir(zotero_dir, database),
            database_path=database,
            linked_attachment_base_dir=linked_attachment_base_dir,
            snapshot=snapshot,
        ) as zotero:
            records = zotero.list_collections()
            forest = build_collection_forest(records)
            selected = [resolve_collection(records, selector) for selector in collections]
            if len({collection.id for collection in selected}) != len(selected):
                raise CollectionError("The same collection was selected more than once")
            exporter = CollectionExporter(
                zotero,
                output,
                recursive=recursive,
                include_non_pdf=not pdf_only,
                overwrite=overwrite,
                dry_run=dry_run,
                prune=prune,
                verify_hashes=verify,
            )
            stats = exporter.export_many(selected, forest)
    except (ZoteroDatabaseError, CollectionError, ExportError, OSError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    if dry_run:
        typer.echo("Dry run; no files were written.")
    _print_stats(stats, show_changes=dry_run or prune)


@app.command()
def status(
    collections: Annotated[
        list[str],
        typer.Argument(help="One or more collection names or collection keys."),
    ],
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Parent directory containing exported workspaces."),
    ] = Path.cwd(),
    recursive: Annotated[
        bool,
        typer.Option("--recursive/--no-recursive", help="Include descendant collections."),
    ] = True,
    pdf_only: Annotated[
        bool,
        typer.Option("--pdf-only/--include-non-pdf", help="Select attachment types."),
    ] = True,
    prune: Annotated[
        bool,
        typer.Option("--prune", help="Show which removed files are safe to prune."),
    ] = False,
    verify: Annotated[
        bool,
        typer.Option("--verify", help="Fully verify source and destination SHA-256 hashes."),
    ] = False,
    zotero_dir: Annotated[
        Path | None,
        typer.Option("--zotero-dir", help="Zotero data directory (default: auto-detect)."),
    ] = None,
    database: Annotated[
        Path | None,
        typer.Option("--database", help="Explicit path to zotero.sqlite."),
    ] = None,
    linked_attachment_base_dir: Annotated[
        Path | None,
        typer.Option("--linked-attachment-base-dir", help="Base for relative linked files."),
    ] = None,
    snapshot: Annotated[
        bool,
        typer.Option("--snapshot", help="Query a temporary SQLite snapshot."),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable diagnostic logging."),
    ] = False,
) -> None:
    """Show synchronization changes without writing anything."""

    configure_logging(verbose)
    try:
        with ZoteroDatabase(
            _data_dir(zotero_dir, database),
            database_path=database,
            linked_attachment_base_dir=linked_attachment_base_dir,
            snapshot=snapshot,
        ) as zotero:
            records = zotero.list_collections()
            forest = build_collection_forest(records)
            selected = [resolve_collection(records, selector) for selector in collections]
            if len({collection.id for collection in selected}) != len(selected):
                raise CollectionError("The same collection was selected more than once")
            stats = CollectionExporter(
                zotero,
                output,
                recursive=recursive,
                include_non_pdf=not pdf_only,
                dry_run=True,
                prune=prune,
                verify_hashes=verify,
            ).export_many(selected, forest)
    except (ZoteroDatabaseError, CollectionError, ExportError, OSError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    _print_stats(stats, show_changes=True)


@app.command()
def doctor(
    zotero_dir: Annotated[
        Path | None,
        typer.Option("--zotero-dir", help="Zotero data directory (default: auto-detect)."),
    ] = None,
    database: Annotated[
        Path | None,
        typer.Option("--database", help="Explicit path to zotero.sqlite."),
    ] = None,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Optional export parent directory to check."),
    ] = None,
    linked_attachment_base_dir: Annotated[
        Path | None,
        typer.Option("--linked-attachment-base-dir", help="Base for relative linked files."),
    ] = None,
    snapshot: Annotated[
        bool,
        typer.Option("--snapshot", help="Test using a temporary SQLite snapshot."),
    ] = False,
) -> None:
    """Diagnose Zotero database, attachment, and output paths."""

    results = run_diagnostics(
        zotero_data_dir=_data_dir(zotero_dir, database),
        database_path=database,
        linked_attachment_base_dir=linked_attachment_base_dir,
        output_root=output,
        snapshot=snapshot,
    )
    for result in results:
        typer.echo(f"[{result.level.upper():7}] {result.message}")
    if any(result.level == "error" for result in results):
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
