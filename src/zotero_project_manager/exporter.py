"""Incremental collection synchronization and status planning."""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
from collections import defaultdict
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from .collections import collection_paths, find_node
from .filenames import attachment_filename, choose_available_name, sanitize_component
from .manifest import Manifest, ManifestEntry, load_manifest, write_manifest
from .models import Collection, CollectionNode, ExportStats, SyncChange, ZoteroAttachment
from .utils import is_within, sha256_file
from .zotero import ZoteroDatabase

LOGGER = logging.getLogger(__name__)
Identity = tuple[str, str]
GatheredAttachment = tuple[Collection, Path, ZoteroAttachment]


class ExportError(RuntimeError):
    """Raised when a synchronization cannot be performed safely."""


class CollectionExporter:
    """Synchronize selected collections into manifest-managed workspaces."""

    def __init__(
        self,
        database: ZoteroDatabase,
        output_root: Path,
        *,
        recursive: bool = True,
        include_non_pdf: bool = False,
        overwrite: bool = False,
        dry_run: bool = False,
        prune: bool = False,
        verify_hashes: bool = False,
    ) -> None:
        self.database = database
        self.output_root = output_root.expanduser().resolve()
        self.recursive = recursive
        self.include_non_pdf = include_non_pdf
        self.overwrite = overwrite
        self.dry_run = dry_run
        self.prune = prune
        self.verify_hashes = verify_hashes
        self._digest_cache: dict[tuple[Path, int, int], str] = {}
        if is_within(self.output_root, database.data_dir):
            raise ExportError(
                f"Refusing to export inside the Zotero data directory: {self.output_root}"
            )

    def export_many(
        self,
        collections: list[Collection],
        forest: list[CollectionNode],
    ) -> list[ExportStats]:
        """Synchronize multiple collections into independent sibling workspaces."""

        results: list[ExportStats] = []
        used_workspaces: set[Path] = set()
        for collection in collections:
            workspace = self._workspace_for(collection, used_workspaces)
            used_workspaces.add(workspace)
            root = find_node(forest, collection.id)
            results.append(self.export_one(root, workspace))
        return results

    def export_one(self, root: CollectionNode, workspace: Path) -> ExportStats:
        """Synchronize one selected collection and, by default, its descendants."""

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

        gathered = self._gather(root)
        original_previous = self._previous_entries(existing_manifest)
        previous = dict(original_previous)
        current_identities = {
            (collection.key, attachment.attachment_key)
            for collection, _, attachment in gathered
        }
        consumed, reconciled = self._reconcile_readded(
            workspace,
            gathered,
            previous,
            current_identities,
        )
        assignments = self._assign_destinations(workspace, gathered, previous)

        entries: list[ManifestEntry] = []
        changes: list[SyncChange] = []
        copied = updated = unchanged = missing = removed = pruned = protected = 0

        for collection, _, attachment in gathered:
            identity = (collection.key, attachment.attachment_key)
            destination = assignments[identity]
            relative_destination = destination.relative_to(workspace).as_posix()
            prior = previous.get(identity)
            source = attachment.source_path

            if source is None or not source.is_file():
                missing += 1
                changes.append(
                    SyncChange("missing", destination, source, attachment.original_path)
                )
                LOGGER.warning(
                    "Missing attachment %s (%s)",
                    attachment.attachment_key,
                    source or attachment.original_path,
                )
                entries.append(
                    replace(
                        prior,
                        item_key=attachment.item_key,
                        attachment_key=attachment.attachment_key,
                        source_path=str(source or attachment.original_path),
                        destination_path=relative_destination,
                        state="missing",
                    )
                    if prior
                    else ManifestEntry(
                        collection_key=collection.key,
                        item_key=attachment.item_key,
                        attachment_key=attachment.attachment_key,
                        source_path=str(source or attachment.original_path),
                        destination_path=relative_destination,
                        source_size=0,
                        source_mtime_ns=0,
                        state="missing",
                    )
                )
                continue

            source_stat = source.stat()
            source_digest = self._source_digest(source, source_stat, prior)
            destination_exists = destination.is_file()
            destination_stat = destination.stat() if destination_exists else None
            is_unchanged = self._destination_matches(
                destination,
                destination_stat,
                source_digest,
                prior,
            )

            if is_unchanged:
                unchanged += 1
            else:
                managed_destination = bool(
                    prior and prior.destination_path == relative_destination
                )
                if destination_exists and (managed_destination or self.overwrite):
                    updated += 1
                    action = "update"
                else:
                    copied += 1
                    action = "copy"
                changes.append(SyncChange(action, destination, source))
                if not self.dry_run:
                    self._atomic_copy(source, destination)
                    destination_stat = destination.stat()
                else:
                    destination_stat = source_stat

            if destination_stat is None:
                destination_stat = source_stat
            entries.append(
                ManifestEntry(
                    collection_key=collection.key,
                    item_key=attachment.item_key,
                    attachment_key=attachment.attachment_key,
                    source_path=str(source),
                    destination_path=relative_destination,
                    source_size=source_stat.st_size,
                    source_mtime_ns=source_stat.st_mtime_ns,
                    source_sha256=source_digest,
                    destination_size=destination_stat.st_size,
                    destination_mtime_ns=destination_stat.st_mtime_ns,
                    state="active",
                )
            )

        for identity, prior in original_previous.items():
            if identity in current_identities or identity in consumed:
                continue
            destination = self._safe_manifest_destination(workspace, prior.destination_path)
            if destination is None:
                removed += 1
                protected += 1
                changes.append(
                    SyncChange("protected", workspace, detail="unsafe manifest destination")
                )
                entries.append(replace(prior, state="removed"))
                continue
            if not destination.is_file():
                continue

            removed += 1
            known_digest = self._known_removed_digest(prior, destination)
            if self.prune and known_digest and self._digest(destination) == known_digest:
                pruned += 1
                changes.append(SyncChange("prune", destination, detail="removed from Zotero"))
                if not self.dry_run:
                    destination.unlink()
                continue
            if self.prune:
                protected += 1
                changes.append(
                    SyncChange(
                        "protected",
                        destination,
                        detail="content changed or no trusted hash is available",
                    )
                )
            else:
                changes.append(SyncChange("removed", destination, detail="retained; use --prune"))
            destination_stat = destination.stat()
            entries.append(
                replace(
                    prior,
                    source_sha256=known_digest,
                    destination_size=destination_stat.st_size,
                    destination_mtime_ns=destination_stat.st_mtime_ns,
                    state="removed",
                )
            )

        for identity in reconciled:
            entry = previous[identity]
            changes.append(
                SyncChange(
                    "reconciled",
                    workspace / entry.destination_path,
                    detail="reused the managed path for a re-added attachment",
                )
            )

        if not self.dry_run:
            workspace.mkdir(parents=True, exist_ok=True)
            manifest = Manifest.create(
                collection_key=root.collection.key,
                collection_name=root.collection.name,
                items=entries,
            )
            write_manifest(manifest_path, manifest)
            self._write_readme(
                workspace / "README.md",
                manifest,
                missing=missing,
                removed=removed - pruned,
            )
            if self.prune:
                self._remove_empty_managed_directories(workspace, changes)

        return ExportStats(
            collection_name=root.collection.name,
            workspace=workspace,
            discovered=len(gathered),
            copied=copied,
            updated=updated,
            unchanged=unchanged,
            missing=missing,
            removed=removed,
            pruned=pruned,
            protected=protected,
            reconciled=len(reconciled),
            changes=tuple(changes),
        )

    def _gather(self, root: CollectionNode) -> list[GatheredAttachment]:
        relative_paths = collection_paths(root, recursive=self.recursive)
        collection_by_id = {
            node.collection.id: node.collection for node in self._walk_selected(root)
        }
        gathered: list[GatheredAttachment] = []
        for collection_id, relative_path in relative_paths.items():
            collection = collection_by_id[collection_id]
            attachments = self.database.attachments_for_collection(
                collection_id,
                include_non_pdf=self.include_non_pdf,
            )
            gathered.extend((collection, relative_path, item) for item in attachments)
        return gathered

    def _reconcile_readded(
        self,
        workspace: Path,
        gathered: list[GatheredAttachment],
        previous: dict[Identity, ManifestEntry],
        current_identities: set[Identity],
    ) -> tuple[set[Identity], set[Identity]]:
        orphaned = [
            (identity, entry)
            for identity, entry in previous.items()
            if identity not in current_identities
        ]
        consumed: set[Identity] = set()
        reconciled: set[Identity] = set()
        for collection, _, attachment in gathered:
            identity = (collection.key, attachment.attachment_key)
            source = attachment.source_path
            if identity in previous or source is None or not source.is_file():
                continue
            source_digest = self._digest(source)
            for old_identity, candidate in orphaned:
                if old_identity in consumed or candidate.collection_key != collection.key:
                    continue
                destination = self._safe_manifest_destination(
                    workspace, candidate.destination_path
                )
                if destination is None or not destination.is_file():
                    continue
                if self._digest(destination) != source_digest:
                    continue
                previous[identity] = replace(
                    candidate,
                    item_key=attachment.item_key,
                    attachment_key=attachment.attachment_key,
                    source_path=str(source),
                    source_sha256=source_digest,
                    state="active",
                )
                consumed.add(old_identity)
                reconciled.add(identity)
                break
        return consumed, reconciled

    def _source_digest(
        self,
        source: Path,
        source_stat: os.stat_result,
        prior: ManifestEntry | None,
    ) -> str:
        if (
            not self.verify_hashes
            and prior
            and prior.source_sha256
            and prior.source_size == source_stat.st_size
            and prior.source_mtime_ns == source_stat.st_mtime_ns
        ):
            return prior.source_sha256
        return self._digest(source)

    def _destination_matches(
        self,
        destination: Path,
        destination_stat: os.stat_result | None,
        source_digest: str,
        prior: ManifestEntry | None,
    ) -> bool:
        if destination_stat is None:
            return False
        if (
            not self.verify_hashes
            and prior
            and prior.source_sha256 == source_digest
            and prior.destination_size == destination_stat.st_size
            and prior.destination_mtime_ns == destination_stat.st_mtime_ns
        ):
            return True
        return self._digest(destination) == source_digest

    def _known_removed_digest(self, prior: ManifestEntry, destination: Path) -> str | None:
        if prior.source_sha256:
            return prior.source_sha256
        source = Path(prior.source_path).expanduser()
        if source.is_file():
            source_digest = self._digest(source)
            if self._digest(destination) == source_digest:
                return source_digest
        return None

    def _digest(self, path: Path) -> str:
        stat = path.stat()
        key = (path.resolve(), stat.st_size, stat.st_mtime_ns)
        if key not in self._digest_cache:
            self._digest_cache[key] = sha256_file(path)
        return self._digest_cache[key]

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
    def _previous_entries(manifest: Manifest | None) -> dict[Identity, ManifestEntry]:
        if manifest is None:
            return {}
        return {(entry.collection_key, entry.attachment_key): entry for entry in manifest.items}

    def _assign_destinations(
        self,
        workspace: Path,
        gathered: list[GatheredAttachment],
        previous: dict[Identity, ManifestEntry],
    ) -> dict[Identity, Path]:
        assignments: dict[Identity, Path] = {}
        reserved: dict[Path, set[str]] = defaultdict(set)

        for collection, relative_dir, attachment in gathered:
            identity = (collection.key, attachment.attachment_key)
            prior = previous.get(identity)
            if prior is None:
                continue
            destination = self._safe_manifest_destination(workspace, prior.destination_path)
            if destination is None or destination.parent != (workspace / relative_dir).resolve():
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
            name = choose_available_name(
                attachment_filename(attachment),
                reserved[directory],
                key=attachment.attachment_key,
            )
            assignments[identity] = directory / name
        return assignments

    @staticmethod
    def _safe_manifest_destination(workspace: Path, relative_path: str) -> Path | None:
        relative = Path(relative_path)
        if relative.is_absolute() or ".." in relative.parts:
            return None
        destination = workspace / relative
        cursor = destination
        while cursor != workspace:
            if cursor.is_symlink():
                return None
            cursor = cursor.parent
        return destination if is_within(destination, workspace) else None

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
    def _remove_empty_managed_directories(
        workspace: Path, changes: list[SyncChange]
    ) -> None:
        parents = sorted(
            {change.destination.parent for change in changes if change.action == "prune"},
            key=lambda path: len(path.parts),
            reverse=True,
        )
        for directory in parents:
            if directory == workspace or not is_within(directory, workspace):
                continue
            try:
                directory.rmdir()
            except OSError:
                pass

    @staticmethod
    def _write_readme(
        path: Path,
        manifest: Manifest,
        *,
        missing: int,
        removed: int,
    ) -> None:
        exported_date = datetime.fromisoformat(manifest.exported_at).astimezone(timezone.utc).date()
        pdf_count = sum(
            1
            for entry in manifest.items
            if entry.state == "active"
            and Path(entry.destination_path).suffix.casefold() == ".pdf"
        )
        content = (
            "# Project exported from Zotero\n\n"
            f"Collection: {manifest.collection_name}\n\n"
            f"Collection key: {manifest.collection_key}\n\n"
            f"Exported: {exported_date.isoformat()}\n\n"
            f"PDF count: {pdf_count}\n\n"
            f"Missing attachments: {missing}\n\n"
            f"Removed attachments retained: {removed}\n"
        )
        path.write_text(content, encoding="utf-8")
