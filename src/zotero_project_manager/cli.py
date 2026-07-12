"""Typer command-line interface for Zotero Project Manager."""

from __future__ import annotations

from pathlib import Path
from dataclasses import replace
from typing import Annotated

import typer

from . import __version__
from .collections import (
    CollectionError,
    build_collection_forest,
    format_collection_forest,
    resolve_collection,
)
from .config import AppConfig, ConfigError, load_config, make_project, save_config
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
project_app = typer.Typer(help="Create and inspect reusable named export projects.")
config_app = typer.Typer(help="Inspect and update global TOML defaults.")
app.add_typer(project_app, name="project")
app.add_typer(config_app, name="config")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"zpm {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option("--version", callback=_version_callback, is_eager=True, help="Show the version."),
    ] = False,
    config: Annotated[
        Path | None,
        typer.Option("--config", help="Use a specific TOML configuration file."),
    ] = None,
) -> None:
    """Run Zotero Project Manager."""

    try:
        ctx.obj = load_config(config)
    except ConfigError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


def _config(ctx: typer.Context) -> AppConfig:
    config = ctx.find_root().obj
    if not isinstance(config, AppConfig):
        raise ConfigError("CLI configuration was not initialized")
    return config


def _data_dir(
    zotero_dir: Path | None,
    database: Path | None,
    config: AppConfig,
) -> Path:
    if zotero_dir is not None:
        return zotero_dir.expanduser()
    if database is not None:
        return database.expanduser().parent
    if config.zotero_dir is not None:
        return config.zotero_dir
    return default_zotero_data_dir()


def _output_dir(output: Path | None, config: AppConfig) -> Path:
    return output or config.output_dir or Path.cwd()


def _linked_dir(explicit: Path | None, config: AppConfig) -> Path | None:
    return explicit or config.linked_attachment_base_dir


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
    ctx: typer.Context,
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
    config = _config(ctx)
    try:
        with ZoteroDatabase(
            _data_dir(zotero_dir, database, config),
            database_path=database,
            snapshot=snapshot,
        ) as zotero:
            forest = build_collection_forest(zotero.list_collections())
            typer.echo(format_collection_forest(forest))
    except (ZoteroDatabaseError, CollectionError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


@app.command()
def export(
    ctx: typer.Context,
    collections: Annotated[
        list[str],
        typer.Argument(help="One or more collection names or collection keys."),
    ],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Parent directory for exported workspaces."),
    ] = None,
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
    metadata: Annotated[
        bool,
        typer.Option(
            "--metadata/--no-metadata",
            help="Generate workspace metadata.json and INDEX.md files.",
        ),
    ] = True,
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
    config = _config(ctx)
    try:
        with ZoteroDatabase(
            _data_dir(zotero_dir, database, config),
            database_path=database,
            linked_attachment_base_dir=_linked_dir(linked_attachment_base_dir, config),
            snapshot=snapshot,
        ) as zotero:
            records = zotero.list_collections()
            forest = build_collection_forest(records)
            selected = [resolve_collection(records, selector) for selector in collections]
            if len({collection.id for collection in selected}) != len(selected):
                raise CollectionError("The same collection was selected more than once")
            exporter = CollectionExporter(
                zotero,
                _output_dir(output, config),
                recursive=recursive,
                include_non_pdf=not pdf_only,
                overwrite=overwrite,
                dry_run=dry_run,
                prune=prune,
                verify_hashes=verify,
                export_metadata=metadata,
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
    ctx: typer.Context,
    collections: Annotated[
        list[str],
        typer.Argument(help="One or more collection names or collection keys."),
    ],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Parent directory containing exported workspaces."),
    ] = None,
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
    config = _config(ctx)
    try:
        with ZoteroDatabase(
            _data_dir(zotero_dir, database, config),
            database_path=database,
            linked_attachment_base_dir=_linked_dir(linked_attachment_base_dir, config),
            snapshot=snapshot,
        ) as zotero:
            records = zotero.list_collections()
            forest = build_collection_forest(records)
            selected = [resolve_collection(records, selector) for selector in collections]
            if len({collection.id for collection in selected}) != len(selected):
                raise CollectionError("The same collection was selected more than once")
            stats = CollectionExporter(
                zotero,
                _output_dir(output, config),
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
    ctx: typer.Context,
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

    config = _config(ctx)
    results = run_diagnostics(
        zotero_data_dir=_data_dir(zotero_dir, database, config),
        database_path=database,
        linked_attachment_base_dir=_linked_dir(linked_attachment_base_dir, config),
        output_root=output or config.output_dir,
        snapshot=snapshot,
    )
    for result in results:
        typer.echo(f"[{result.level.upper():7}] {result.message}")
    if any(result.level == "error" for result in results):
        raise typer.Exit(code=1)


@project_app.command("add")
def add_project(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Short project name used by zpm sync.")],
    collections: Annotated[
        list[str], typer.Argument(help="One or more Zotero collection names or keys.")
    ],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Override the global output directory."),
    ] = None,
    recursive: Annotated[
        bool, typer.Option("--recursive/--no-recursive", help="Include descendants.")
    ] = True,
    include_non_pdf: Annotated[
        bool, typer.Option("--include-non-pdf", help="Include non-PDF attachments.")
    ] = False,
    prune: Annotated[
        bool, typer.Option("--prune", help="Safely prune removed managed files during sync.")
    ] = False,
    verify: Annotated[
        bool, typer.Option("--verify", help="Fully verify hashes during sync.")
    ] = False,
    metadata: Annotated[
        bool,
        typer.Option("--metadata/--no-metadata", help="Generate metadata during sync."),
    ] = True,
    force: Annotated[
        bool, typer.Option("--force", help="Replace an existing project with this name.")
    ] = False,
) -> None:
    """Add a reusable named project to the TOML configuration."""

    config = _config(ctx)
    if name in config.projects and not force:
        typer.echo(f"Error: Project {name!r} already exists; use --force to replace it", err=True)
        raise typer.Exit(code=1)
    try:
        project = make_project(
            name,
            collections,
            output_dir=output,
            recursive=recursive,
            include_non_pdf=include_non_pdf,
            prune=prune,
            verify=verify,
            metadata=metadata,
        )
        updated = config.with_project(project)
        save_config(updated)
        ctx.find_root().obj = updated
    except (ConfigError, OSError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Saved project {name!r} in {config.path}")


@config_app.command("set")
def set_config(
    ctx: typer.Context,
    zotero_dir: Annotated[
        Path | None, typer.Option("--zotero-dir", help="Default Zotero data directory.")
    ] = None,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Default export parent directory.")
    ] = None,
    linked_attachment_base_dir: Annotated[
        Path | None,
        typer.Option("--linked-attachment-base-dir", help="Default linked attachment base."),
    ] = None,
) -> None:
    """Set one or more global configuration defaults."""

    config = _config(ctx)
    if zotero_dir is None and output is None and linked_attachment_base_dir is None:
        typer.echo("Error: Provide at least one setting to update", err=True)
        raise typer.Exit(code=1)
    updated = replace(
        config,
        zotero_dir=(
            zotero_dir.expanduser().resolve() if zotero_dir is not None else config.zotero_dir
        ),
        output_dir=(output.expanduser().resolve() if output is not None else config.output_dir),
        linked_attachment_base_dir=(
            linked_attachment_base_dir.expanduser().resolve()
            if linked_attachment_base_dir is not None
            else config.linked_attachment_base_dir
        ),
    )
    try:
        save_config(updated)
        ctx.find_root().obj = updated
    except OSError as exc:
        typer.echo(f"Error: Could not write configuration: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Updated {config.path}")


@config_app.command("show")
def show_config(ctx: typer.Context) -> None:
    """Show the active configuration path and global defaults."""

    config = _config(ctx)
    typer.echo(f"Config: {config.path}")
    typer.echo(f"Zotero directory: {config.zotero_dir or '(auto-detect)'}")
    typer.echo(f"Output directory: {config.output_dir or '(current directory)'}")
    typer.echo(
        "Linked attachment base: "
        f"{config.linked_attachment_base_dir or '(not configured)'}"
    )
    typer.echo(f"Named projects: {len(config.projects)}")


@project_app.command("list")
def list_projects(ctx: typer.Context) -> None:
    """List configured named projects."""

    config = _config(ctx)
    if not config.projects:
        typer.echo(f"No projects configured in {config.path}")
        return
    for name in sorted(config.projects, key=str.casefold):
        project = config.projects[name]
        output = project.output_dir or config.output_dir or Path.cwd()
        typer.echo(f"{name}: {', '.join(project.collections)} -> {output}")


@project_app.command("show")
def show_project(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Configured project name.")],
) -> None:
    """Show all settings for one named project."""

    config = _config(ctx)
    project = config.projects.get(name)
    if project is None:
        typer.echo(f"Error: No configured project named {name!r}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"Name: {project.name}")
    typer.echo(f"Collections: {', '.join(project.collections)}")
    typer.echo(f"Output: {project.output_dir or config.output_dir or Path.cwd()}")
    typer.echo(f"Recursive: {project.recursive}")
    typer.echo(f"Include non-PDF: {project.include_non_pdf}")
    typer.echo(f"Prune: {project.prune}")
    typer.echo(f"Verify: {project.verify}")
    typer.echo(f"Metadata: {project.metadata}")


@app.command()
def sync(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Configured project name.")],
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Report actions without writing files.")
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable diagnostic logging.")
    ] = False,
) -> None:
    """Synchronize a named project using its saved settings."""

    configure_logging(verbose)
    config = _config(ctx)
    project = config.projects.get(name)
    if project is None:
        typer.echo(f"Error: No configured project named {name!r}", err=True)
        raise typer.Exit(code=1)
    try:
        with ZoteroDatabase(
            _data_dir(None, None, config),
            linked_attachment_base_dir=config.linked_attachment_base_dir,
        ) as zotero:
            records = zotero.list_collections()
            forest = build_collection_forest(records)
            selected = [
                resolve_collection(records, selector) for selector in project.collections
            ]
            stats = CollectionExporter(
                zotero,
                project.output_dir or config.output_dir or Path.cwd(),
                recursive=project.recursive,
                include_non_pdf=project.include_non_pdf,
                dry_run=dry_run,
                prune=project.prune,
                verify_hashes=project.verify,
                export_metadata=project.metadata,
            ).export_many(selected, forest)
    except (ZoteroDatabaseError, CollectionError, ExportError, OSError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    if dry_run:
        typer.echo("Dry run; no files were written.")
    _print_stats(stats, show_changes=dry_run or project.prune)


if __name__ == "__main__":
    app()
