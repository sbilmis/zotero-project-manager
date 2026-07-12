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
