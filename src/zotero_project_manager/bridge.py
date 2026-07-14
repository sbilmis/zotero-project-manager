"""Validated snapshots produced by the Zotero companion plugin."""

from __future__ import annotations

import json
from dataclasses import MISSING, fields
from pathlib import Path
from typing import Any, TypeVar

from .models import Collection, ZoteroAnnotation, ZoteroAttachment, ZoteroNote


BRIDGE_SCHEMA_VERSION = 1
MAX_BRIDGE_SIZE = 100 * 1024 * 1024


class BridgeError(RuntimeError):
    """Raised when a companion-plugin snapshot is invalid or unsafe."""


Model = TypeVar("Model", Collection, ZoteroAnnotation, ZoteroAttachment, ZoteroNote)


class BridgeSource:
    """Expose a validated plugin snapshot through the standard source interface."""

    def __init__(
        self,
        *,
        data_dir: Path,
        zotero_version: str,
        collections: list[Collection],
        attachments: dict[int, list[ZoteroAttachment]],
        annotations: dict[int, tuple[ZoteroAnnotation, ...]],
        notes: dict[int, tuple[ZoteroNote, ...]],
    ) -> None:
        self.data_dir = data_dir.expanduser().resolve()
        self.zotero_version = zotero_version
        self._collections = collections
        self._attachments = attachments
        self._annotations = annotations
        self._notes = notes

    @classmethod
    def load(cls, path: Path) -> "BridgeSource":
        """Load and validate a JSON snapshot written by the companion plugin."""

        request = path.expanduser().resolve()
        try:
            size = request.stat().st_size
        except OSError as exc:
            raise BridgeError(f"Plugin snapshot cannot be read: {request}: {exc}") from exc
        if size > MAX_BRIDGE_SIZE:
            raise BridgeError(
                f"Plugin snapshot is too large ({size} bytes; limit {MAX_BRIDGE_SIZE})"
            )
        try:
            payload = json.loads(request.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise BridgeError(f"Plugin snapshot is not valid UTF-8 JSON: {request}: {exc}") from exc
        if not isinstance(payload, dict):
            raise BridgeError("Plugin snapshot root must be a JSON object")
        if payload.get("schema_version") != BRIDGE_SCHEMA_VERSION:
            raise BridgeError(
                f"Unsupported plugin snapshot schema {payload.get('schema_version')!r}; "
                f"expected {BRIDGE_SCHEMA_VERSION}"
            )

        try:
            data_dir = Path(_required_string(payload, "data_dir"))
            zotero_version = _required_string(payload, "zotero_version")
            collections = [
                _model(Collection, value) for value in _required_list(payload, "collections")
            ]
            attachments = _grouped_models(
                payload, "attachments", ZoteroAttachment, path_fields={"source_path"}
            )
            annotations = _grouped_models(
                payload, "annotations", ZoteroAnnotation, path_fields={"image_path"}
            )
            notes = _grouped_models(payload, "notes", ZoteroNote)
        except (KeyError, TypeError, ValueError) as exc:
            raise BridgeError(f"Invalid plugin snapshot: {exc}") from exc

        if not data_dir.is_absolute():
            raise BridgeError("Plugin snapshot data_dir must be absolute")
        cache_root = (data_dir / "cache").resolve()
        for values in annotations.values():
            for annotation in values:
                if annotation.image_path and (
                    annotation.image_path.suffix.casefold() != ".png"
                    or not _is_within(annotation.image_path, cache_root)
                ):
                    raise BridgeError(
                        "Plugin annotation image must be a PNG inside Zotero's cache: "
                        f"{annotation.image_path}"
                    )
        collection_ids = {collection.id for collection in collections}
        unknown = set(attachments) - collection_ids
        if unknown:
            raise BridgeError(f"Attachments reference unknown collection IDs: {sorted(unknown)}")
        return cls(
            data_dir=data_dir,
            zotero_version=zotero_version,
            collections=collections,
            attachments=attachments,
            annotations={key: tuple(value) for key, value in annotations.items()},
            notes={key: tuple(value) for key, value in notes.items()},
        )

    def list_collections(self) -> list[Collection]:
        """Return collections captured by Zotero."""

        return list(self._collections)

    def attachments_for_collection(
        self,
        collection_id: int,
        *,
        include_non_pdf: bool = False,
    ) -> list[ZoteroAttachment]:
        """Return captured attachments, applying zpm's file-type policy."""

        attachments = list(self._attachments.get(collection_id, ()))
        if include_non_pdf:
            return attachments
        return [
            attachment
            for attachment in attachments
            if (attachment.content_type or "").casefold() == "application/pdf"
            or attachment.original_path.casefold().endswith(".pdf")
        ]

    def annotations_for_attachment(
        self, attachment_id: int
    ) -> tuple[ZoteroAnnotation, ...]:
        """Return captured annotations for one attachment."""

        return self._annotations.get(attachment_id, ())

    def child_notes_for_item(
        self,
        item_id: int,
        *,
        attachment_id: int | None = None,
    ) -> tuple[ZoteroNote, ...]:
        """Return deduplicated captured notes for an item and attachment."""

        parent_ids = (item_id,) if attachment_id is None else (item_id, attachment_id)
        notes: list[ZoteroNote] = []
        seen: set[int] = set()
        for parent_id in parent_ids:
            for note in self._notes.get(parent_id, ()):
                if note.note_id not in seen:
                    notes.append(note)
                    seen.add(note.note_id)
        return tuple(notes)


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload[key]
    if not isinstance(value, str) or not value:
        raise TypeError(f"{key} must be a non-empty string")
    return value


def _required_list(payload: dict[str, Any], key: str) -> list[Any]:
    value = payload[key]
    if not isinstance(value, list):
        raise TypeError(f"{key} must be a list")
    return value


def _model(
    model_type: type[Model],
    value: Any,
    *,
    path_fields: set[str] | None = None,
) -> Model:
    if not isinstance(value, dict):
        raise TypeError(f"{model_type.__name__} entry must be an object")
    names = {field.name for field in fields(model_type)}
    unknown = set(value) - names
    missing = {
        field.name
        for field in fields(model_type)
        if field.default is MISSING
        and field.default_factory is MISSING
        and field.name not in value
    }
    if unknown:
        raise TypeError(f"{model_type.__name__} has unknown fields: {sorted(unknown)}")
    if missing:
        raise TypeError(f"{model_type.__name__} is missing fields: {sorted(missing)}")
    converted = dict(value)
    for name in path_fields or ():
        raw = converted.get(name)
        converted[name] = Path(raw).expanduser().resolve() if raw else None
    for name in ("creators", "tags"):
        if name in converted:
            if not isinstance(converted[name], list):
                raise TypeError(f"{model_type.__name__}.{name} must be a list")
            converted[name] = tuple(str(item) for item in converted[name])
    return model_type(**converted)


def _grouped_models(
    payload: dict[str, Any],
    key: str,
    model_type: type[Model],
    *,
    path_fields: set[str] | None = None,
) -> dict[int, list[Model]]:
    raw = payload[key]
    if not isinstance(raw, dict):
        raise TypeError(f"{key} must be an object grouped by numeric ID")
    result: dict[int, list[Model]] = {}
    for raw_id, values in raw.items():
        group_id = int(raw_id)
        if not isinstance(values, list):
            raise TypeError(f"{key}.{raw_id} must be a list")
        result[group_id] = [
            _model(model_type, value, path_fields=path_fields) for value in values
        ]
    return result


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True
