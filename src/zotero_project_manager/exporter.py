"""Incremental collection export orchestration."""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from .collections import collection_paths, find_node
from .filenames import attachment_filename, choose_available_name, sanitize_component
from .manifest import Manifest, ManifestEntry, load_manifest, write_manifest
from .models import Collection, CollectionNode, ExportStats, ZoteroAttachment
from .utils import is_within
from .zotero import ZoteroDatabase

LOGGER = logging.getLogger(__name__)


class ExportError(RuntimeError):
    """Raised when an export cannot be performed safely."""


class CollectionExporter:
    """Export selected collections into manifest-managed workspaces."""

    def __init__(
        self,
        database: ZoteroDatabase,
        output_root: Path,
        *,
        recursive: bool = True,
        include_non_pdf: bool = False,
        overwrite: bool = False,
        dry_run: bool = False,
    ) -> None:
        self.database = database
        self.output_root = output_root.expanduser().resolve()
        self.recursive = recursive
        self.include_non_pdf = include_non_pdf
        self.overwrite = overwrite
        self.dry_run = dry_run
        if is_within(self.output_root, database.data_dir):
            raise ExportError(
                f"Refusing to export inside the Zotero data directory: {self.output_root}"
            )

    def export_many(
        self,
        collections: list[Collection],
        forest: list[CollectionNode],
    ) -> list[ExportStats]:
        """Export multiple collections into independent sibling workspaces."""

        results: list[ExportStats] = []
        used_workspaces: set[Path] = set()
        for collection in collections:
            workspace = self._workspace_for(collection, used_workspaces)
            used_workspaces.add(workspace)
            root = find_node(forest, collection.id)
            results.append(self.export_one(root, workspace))
        return results

    def export_one(self, root: CollectionNode, workspace: Path) -> ExportStats:
        """Export one selected collection and, by default, all descendants."""

        workspace = workspace.resolve()
        if not is_within(workspace, self.output_root):
            raise ExportError(f"Workspace resolves outside the output directory: {workspace}")
        manifest_path = workspace / "manifest.json"
        existing_manifest = load_manifest(manifest_path)
        if workspace.exists() and existing_manifest is None and not self.overwrite:
            raise ExportError(
                f"Destination exists but is not managed by zpm: {workspace}. "
                "Use --overwrite to adopt it."
            )
        if existing_manifest and existing_manifest.collection_key != root.collection.key:
            raise ExportError(
                f"Destination manifest belongs to collection {existing_manifest.collection_key}, "
                f"not {root.collection.key}: {workspace}"
            )

        relative_paths = collection_paths(root, recursive=self.recursive)
        collection_by_id = {
            node.collection.id: node.collection for node in self._walk_selected(root)
        }
        gathered: list[tuple[Collection, Path, ZoteroAttachment]] = []
        for collection_id, relative_path in relative_paths.items():
            collection = collection_by_id[collection_id]
            attachments = self.database.attachments_for_collection(
                collection_id,
                include_non_pdf=self.include_non_pdf,
            )
            gathered.extend((collection, relative_path, attachment) for attachment in attachments)

        previous = self._previous_entries(existing_manifest)
        assignments = self._assign_destinations(workspace, gathered, previous)
        entries: list[ManifestEntry] = []
        copied = updated = unchanged = missing = 0

        for collection, _, attachment in gathered:
            identity = (collection.key, attachment.attachment_key)
            destination = assignments[identity]
            source = attachment.source_path
            if source is None or not source.is_file():
                missing += 1
                LOGGER.warning(
                    "Missing attachment %s (%s)", attachment.attachment_key, source or attachment.original_path
                )
                if prior is not None:
                    entries.append(prior)
                continue

            stat = source.stat()
            relative_destination = destination.relative_to(workspace).as_posix()
            prior = previous.get(identity)
            is_unchanged = bool(
                prior
                and prior.destination_path == relative_destination
                and prior.source_size == stat.st_size
                and prior.source_mtime_ns == stat.st_mtime_ns
                and destination.is_file()
            )
            if is_unchanged:
                unchanged += 1
            else:
                existed_as_managed = bool(prior and destination.exists())
                if existed_as_managed or (destination.exists() and self.overwrite):
                    updated += 1
                else:
                    copied += 1
                if not self.dry_run:
                    self._atomic_copy(source, destination)

            entries.append(
                ManifestEntry(
                    collection_key=collection.key,
                    item_key=attachment.item_key,
                    attachment_key=attachment.attachment_key,
                    source_path=str(source),
                    destination_path=relative_destination,
                    source_size=stat.st_size,
                    source_mtime_ns=stat.st_mtime_ns,
                )
            )

        current_identities = {
            (collection.key, attachment.attachment_key)
            for collection, _, attachment in gathered
        }
        for identity, prior in previous.items():
            if identity not in current_identities and (workspace / prior.destination_path).is_file():
                entries.append(prior)

        if not self.dry_run:
            workspace.mkdir(parents=True, exist_ok=True)
            manifest = Manifest.create(
                collection_key=root.collection.key,
                collection_name=root.collection.name,
                items=entries,
            )
            write_manifest(manifest_path, manifest)
            self._write_readme(workspace / "README.md", manifest, missing)

        return ExportStats(
            collection_name=root.collection.name,
            workspace=workspace,
            discovered=len(gathered),
            copied=copied,
            updated=updated,
            unchanged=unchanged,
            missing=missing,
        )

    def _workspace_for(self, collection: Collection, used: set[Path]) -> Path:
        base_name = sanitize_component(collection.name)
        candidate = self.output_root / base_name
        existing = load_manifest(candidate / "manifest.json")
        if candidate in used or (existing and existing.collection_key != collection.key):
            candidate = self.output_root / f"{base_name} [{collection.key}]"
        if candidate in used:
            raise ExportError(f"Collection was selected more than once: {collection.name}")
        return candidate

    def _walk_selected(self, root: CollectionNode) -> list[CollectionNode]:
        nodes = [root]
        if not self.recursive:
            return nodes
        for child in root.children:
            nodes.extend(self._walk_selected(child))
        return nodes

    @staticmethod
    def _previous_entries(
        manifest: Manifest | None,
    ) -> dict[tuple[str, str], ManifestEntry]:
        if manifest is None:
            return {}
        return {(entry.collection_key, entry.attachment_key): entry for entry in manifest.items}

    def _assign_destinations(
        self,
        workspace: Path,
        gathered: list[tuple[Collection, Path, ZoteroAttachment]],
        previous: dict[tuple[str, str], ManifestEntry],
    ) -> dict[tuple[str, str], Path]:
        assignments: dict[tuple[str, str], Path] = {}
        reserved: dict[Path, set[str]] = defaultdict(set)

        for collection, relative_dir, attachment in gathered:
            identity = (collection.key, attachment.attachment_key)
            prior = previous.get(identity)
            if prior is None:
                continue
            destination = (workspace / prior.destination_path).resolve()
            if not is_within(destination, workspace) or destination.parent != (
                workspace / relative_dir
            ).resolve():
                continue
            assignments[identity] = destination
            reserved[destination.parent].add(destination.name.casefold())

        if workspace.exists() and not self.overwrite:
            for path in workspace.rglob("*"):
                if path.is_file() and path.name not in {"manifest.json", "README.md"}:
                    reserved[path.parent.resolve()].add(path.name.casefold())

        for collection, relative_dir, attachment in gathered:
            identity = (collection.key, attachment.attachment_key)
            if identity in assignments:
                continue
            directory = (workspace / relative_dir).resolve()
            if not is_within(directory, workspace):
                raise ExportError(f"Collection directory resolves outside the workspace: {directory}")
            desired = attachment_filename(attachment)
            name = choose_available_name(
                desired,
                reserved[directory],
                key=attachment.attachment_key,
            )
            assignments[identity] = directory / name
        return assignments

    @staticmethod
    def _atomic_copy(source: Path, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{destination.name}.", dir=destination.parent
        )
        os.close(descriptor)
        temporary_path = Path(temporary_name)
        try:
            shutil.copy2(source, temporary_path)
            temporary_path.replace(destination)
        except BaseException:
            temporary_path.unlink(missing_ok=True)
            raise

    @staticmethod
    def _write_readme(path: Path, manifest: Manifest, missing: int) -> None:
        exported_date = datetime.fromisoformat(manifest.exported_at).astimezone(timezone.utc).date()
        pdf_count = sum(
            1 for entry in manifest.items if Path(entry.destination_path).suffix.casefold() == ".pdf"
        )
        content = (
            "# Project exported from Zotero\n\n"
            f"Collection: {manifest.collection_name}\n\n"
            f"Collection key: {manifest.collection_key}\n\n"
            f"Exported: {exported_date.isoformat()}\n\n"
            f"PDF count: {pdf_count}\n\n"
            f"Missing attachments: {missing}\n"
        )
        path.write_text(content, encoding="utf-8")
