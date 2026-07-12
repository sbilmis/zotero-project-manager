"""Versioned manifest serialization for incremental exports."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MANIFEST_VERSION = 1


@dataclass(frozen=True, slots=True)
class ManifestEntry:
    """One exported Zotero attachment."""

    collection_key: str
    item_key: str
    attachment_key: str
    source_path: str
    destination_path: str
    source_size: int
    source_mtime_ns: int


@dataclass(frozen=True, slots=True)
class Manifest:
    """Metadata needed to update an exported workspace incrementally."""

    version: int
    exported_at: str
    collection_key: str
    collection_name: str
    items: tuple[ManifestEntry, ...]

    @classmethod
    def create(
        cls,
        *,
        collection_key: str,
        collection_name: str,
        items: list[ManifestEntry],
        exported_at: datetime | None = None,
    ) -> "Manifest":
        """Create a current-version manifest with a UTC timestamp."""

        timestamp = exported_at or datetime.now(timezone.utc)
        return cls(
            version=MANIFEST_VERSION,
            exported_at=timestamp.isoformat(timespec="seconds"),
            collection_key=collection_key,
            collection_name=collection_name,
            items=tuple(items),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert the manifest into its stable JSON representation."""

        return {
            "version": self.version,
            "exported_at": self.exported_at,
            "collection_key": self.collection_key,
            "collection_name": self.collection_name,
            "items": [asdict(item) for item in self.items],
        }


def load_manifest(path: Path) -> Manifest | None:
    """Load an existing manifest, returning ``None`` when absent."""

    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("version") != MANIFEST_VERSION:
            return None
        return Manifest(
            version=int(payload["version"]),
            exported_at=str(payload["exported_at"]),
            collection_key=str(payload["collection_key"]),
            collection_name=str(payload["collection_name"]),
            items=tuple(ManifestEntry(**item) for item in payload["items"]),
        )
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return None


def write_manifest(path: Path, manifest: Manifest) -> None:
    """Atomically write a manifest as human-readable UTF-8 JSON."""

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(manifest.to_dict(), handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        temporary_path.replace(path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise
