"""Strictly read-only access to Zotero's SQLite database."""

from __future__ import annotations

import logging
import sqlite3
import tempfile
from pathlib import Path
from types import TracebackType
from urllib.parse import unquote, urlparse

from .models import Collection, ZoteroAttachment

LOGGER = logging.getLogger(__name__)


class ZoteroDatabaseError(RuntimeError):
    """Raised when the Zotero database cannot be found or read."""


def _database_error(operation: str, error: sqlite3.Error) -> ZoteroDatabaseError:
    """Translate SQLite failures into actionable, user-facing errors."""

    detail = str(error)
    if "locked" in detail.casefold() or "busy" in detail.casefold():
        return ZoteroDatabaseError(
            "Zotero's database is temporarily locked, usually because Zotero is "
            "syncing or performing maintenance. Wait for that operation to finish and "
            "retry. If the lock persists, close Zotero completely and run the command "
            "again. zpm requested read-only access and made no changes."
        )
    return ZoteroDatabaseError(f"{operation}: {detail}")


def default_zotero_data_dir() -> Path:
    """Return the first existing standard Zotero data directory."""

    candidates = (
        Path.home() / "Zotero",
        Path.home() / "Documents" / "Zotero",
    )
    for candidate in candidates:
        if (candidate / "zotero.sqlite").is_file():
            return candidate
    return candidates[0]


class ZoteroDatabase:
    """Read Zotero through a query-only connection, normally from a snapshot."""

    def __init__(
        self,
        zotero_data_dir: Path | None = None,
        *,
        database_path: Path | None = None,
        linked_attachment_base_dir: Path | None = None,
        snapshot: bool = False,
    ) -> None:
        self.data_dir = (zotero_data_dir or default_zotero_data_dir()).expanduser().resolve()
        self.database_path = (
            database_path.expanduser().resolve()
            if database_path
            else self.data_dir / "zotero.sqlite"
        )
        self.linked_attachment_base_dir = (
            linked_attachment_base_dir.expanduser().resolve()
            if linked_attachment_base_dir
            else None
        )
        self.snapshot = snapshot
        self._connection: sqlite3.Connection | None = None
        self._temporary_directory: tempfile.TemporaryDirectory[str] | None = None

    def __enter__(self) -> "ZoteroDatabase":
        self.open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def open(self) -> None:
        """Open the database without ever requesting write access."""

        if self._connection is not None:
            return
        if not self.database_path.is_file():
            raise ZoteroDatabaseError(f"Zotero database not found: {self.database_path}")

        try:
            source = self._connect_read_only(self.database_path)
            if self.snapshot:
                self._temporary_directory = tempfile.TemporaryDirectory(prefix="zpm-")
                snapshot_path = Path(self._temporary_directory.name) / "zotero.sqlite"
                snapshot_connection = sqlite3.connect(snapshot_path)
                try:
                    source.backup(snapshot_connection)
                finally:
                    snapshot_connection.close()
                    source.close()
                self._connection = self._connect_read_only(snapshot_path)
            else:
                self._connection = source
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA query_only = ON")
            self._connection.execute("BEGIN")
        except sqlite3.Error as exc:
            self.close()
            raise _database_error("Could not read Zotero database", exc) from exc

    def close(self) -> None:
        """Close the read-only connection and remove any temporary snapshot."""

        if self._connection is not None:
            self._connection.close()
            self._connection = None
        if self._temporary_directory is not None:
            self._temporary_directory.cleanup()
            self._temporary_directory = None

    @staticmethod
    def _connect_read_only(path: Path) -> sqlite3.Connection:
        uri = f"{path.resolve().as_uri()}?mode=ro"
        connection = sqlite3.connect(uri, uri=True, timeout=10)
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    @property
    def connection(self) -> sqlite3.Connection:
        """Return the active connection or fail with a helpful error."""

        if self._connection is None:
            raise ZoteroDatabaseError("ZoteroDatabase must be opened before querying")
        return self._connection

    def list_collections(self) -> list[Collection]:
        """Return every Zotero collection sorted independently of display order."""

        try:
            rows = self.connection.execute(
                """
                SELECT collectionID, key, collectionName, parentCollectionID, libraryID
                FROM collections
                ORDER BY libraryID, collectionName COLLATE NOCASE, key
                """
            ).fetchall()
        except sqlite3.Error as exc:
            raise _database_error("Could not list Zotero collections", exc) from exc
        return [
            Collection(
                id=int(row["collectionID"]),
                key=str(row["key"]),
                name=str(row["collectionName"]),
                parent_id=(
                    int(row["parentCollectionID"])
                    if row["parentCollectionID"] is not None
                    else None
                ),
                library_id=int(row["libraryID"]),
            )
            for row in rows
        ]

    def attachments_for_collection(
        self,
        collection_id: int,
        *,
        include_non_pdf: bool = False,
    ) -> list[ZoteroAttachment]:
        """Return local attachments belonging directly to one collection."""

        try:
            rows = self.connection.execute(
                """
                WITH selected_items AS (
                    SELECT itemID FROM collectionItems WHERE collectionID = ?
                )
                SELECT DISTINCT
                    attachment.itemID AS attachmentID,
                    attachment.key AS attachmentKey,
                    COALESCE(parent.itemID, attachment.itemID) AS metadataItemID,
                    COALESCE(parent.key, attachment.key) AS metadataItemKey,
                    itemAttachments.path AS attachmentPath,
                    itemAttachments.contentType AS contentType
                FROM itemAttachments
                JOIN items AS attachment ON attachment.itemID = itemAttachments.itemID
                LEFT JOIN items AS parent ON parent.itemID = itemAttachments.parentItemID
                WHERE itemAttachments.path IS NOT NULL
                  AND (
                      attachment.itemID IN selected_items
                      OR itemAttachments.parentItemID IN selected_items
                  )
                ORDER BY metadataItemID, attachmentID
                """,
                (collection_id,),
            ).fetchall()
        except sqlite3.Error as exc:
            raise _database_error("Could not read collection items", exc) from exc

        attachments: list[ZoteroAttachment] = []
        for row in rows:
            original_path = str(row["attachmentPath"])
            content_type = str(row["contentType"]) if row["contentType"] else None
            if not include_non_pdf and not self._is_pdf(content_type, original_path):
                continue
            item_id = int(row["metadataItemID"])
            metadata = self._item_metadata(item_id)
            attachment_key = str(row["attachmentKey"])
            attachments.append(
                ZoteroAttachment(
                    attachment_id=int(row["attachmentID"]),
                    attachment_key=attachment_key,
                    item_id=item_id,
                    item_key=str(row["metadataItemKey"]),
                    title=metadata.get("title"),
                    date=metadata.get("date"),
                    creators=self._item_creators(item_id),
                    content_type=content_type,
                    source_path=self.resolve_attachment_path(original_path, attachment_key),
                    original_path=original_path,
                )
            )
        return attachments

    def _item_metadata(self, item_id: int) -> dict[str, str]:
        try:
            rows = self.connection.execute(
                """
                SELECT fields.fieldName, itemDataValues.value
                FROM itemData
                JOIN fields ON fields.fieldID = itemData.fieldID
                JOIN itemDataValues ON itemDataValues.valueID = itemData.valueID
                WHERE itemData.itemID = ? AND fields.fieldName IN ('title', 'date')
                """,
                (item_id,),
            ).fetchall()
        except sqlite3.Error as exc:
            raise _database_error("Could not read item metadata", exc) from exc
        return {str(row["fieldName"]): str(row["value"]) for row in rows}

    def _item_creators(self, item_id: int) -> tuple[str, ...]:
        try:
            rows = self.connection.execute(
                """
                SELECT creators.firstName, creators.lastName, creators.fieldMode
                FROM itemCreators
                JOIN creators ON creators.creatorID = itemCreators.creatorID
                WHERE itemCreators.itemID = ?
                ORDER BY itemCreators.orderIndex
                """,
                (item_id,),
            ).fetchall()
        except sqlite3.Error as exc:
            raise _database_error("Could not read item creators", exc) from exc
        names: list[str] = []
        for row in rows:
            last_name = str(row["lastName"] or "").strip()
            first_name = str(row["firstName"] or "").strip()
            name = last_name or first_name
            if name:
                names.append(name)
        return tuple(names)

    def resolve_attachment_path(self, stored_path: str, attachment_key: str) -> Path | None:
        """Resolve Zotero's storage, absolute, URI, or linked-relative path syntax."""

        if stored_path.startswith("storage:"):
            relative = stored_path.removeprefix("storage:")
            return (self.data_dir / "storage" / attachment_key / relative).resolve()
        if stored_path.startswith("attachments:"):
            if self.linked_attachment_base_dir is None:
                LOGGER.warning(
                    "Cannot resolve linked attachment %s without --linked-attachment-base-dir",
                    stored_path,
                )
                return None
            relative = stored_path.removeprefix("attachments:")
            return (self.linked_attachment_base_dir / relative).resolve()
        if stored_path.startswith("file://"):
            parsed = urlparse(stored_path)
            return Path(unquote(parsed.path)).expanduser().resolve()

        path = Path(stored_path).expanduser()
        if path.is_absolute():
            return path.resolve()
        if self.linked_attachment_base_dir is not None:
            return (self.linked_attachment_base_dir / path).resolve()
        return None

    @staticmethod
    def _is_pdf(content_type: str | None, stored_path: str) -> bool:
        return (content_type or "").casefold() == "application/pdf" or stored_path.casefold().endswith(
            ".pdf"
        )
