"""Read-only source interface consumed by the workspace exporter."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from .models import Collection, ZoteroAnnotation, ZoteroAttachment, ZoteroNote


class ZoteroSource(Protocol):
    """A read-only provider of Zotero collections and attachment metadata."""

    data_dir: Path

    def list_collections(self) -> list[Collection]:
        """Return all collections visible to this source."""

    def attachments_for_collection(
        self,
        collection_id: int,
        *,
        include_non_pdf: bool = False,
    ) -> list[ZoteroAttachment]:
        """Return attachments belonging directly to one collection."""

    def annotations_for_attachment(
        self, attachment_id: int
    ) -> tuple[ZoteroAnnotation, ...]:
        """Return annotations belonging to an attachment."""

    def child_notes_for_item(
        self,
        item_id: int,
        *,
        attachment_id: int | None = None,
    ) -> tuple[ZoteroNote, ...]:
        """Return notes belonging to an item and optionally its attachment."""
