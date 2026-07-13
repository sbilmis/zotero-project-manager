"""Domain models shared by the application."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Collection:
    """A Zotero collection."""

    id: int
    key: str
    name: str
    parent_id: int | None
    library_id: int


@dataclass(slots=True)
class CollectionNode:
    """A collection and its child collections."""

    collection: Collection
    children: list["CollectionNode"] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ZoteroAttachment:
    """An exportable attachment with its parent item's metadata."""

    attachment_id: int
    attachment_key: str
    item_id: int
    item_key: str
    title: str | None
    date: str | None
    creators: tuple[str, ...]
    content_type: str | None
    source_path: Path | None
    original_path: str
    doi: str | None = None
    tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ZoteroAnnotation:
    """A read-only Zotero PDF annotation."""

    annotation_id: int
    annotation_key: str
    attachment_id: int
    annotation_type: str
    text: str | None
    comment: str | None
    color: str | None
    page_label: str | None
    sort_index: str
    position: str
    author_name: str | None
    date_added: str
    date_modified: str
    tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ZoteroNote:
    """A read-only child note belonging to a Zotero item or attachment."""

    note_id: int
    note_key: str
    parent_item_id: int
    title: str | None
    content: str
    date_added: str
    date_modified: str
    tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ExportStats:
    """Counters produced by a single collection export."""

    collection_name: str
    workspace: Path
    discovered: int
    copied: int
    updated: int
    unchanged: int
    missing: int
    removed: int = 0
    pruned: int = 0
    protected: int = 0
    reconciled: int = 0
    annotation_files: int = 0
    annotations: int = 0
    notes: int = 0
    changes: tuple["SyncChange", ...] = ()


@dataclass(frozen=True, slots=True)
class SyncChange:
    """A planned or completed synchronization action."""

    action: str
    destination: Path
    source: Path | None = None
    detail: str | None = None
