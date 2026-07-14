from datetime import datetime, timezone
import json
from pathlib import Path

from zotero_project_manager.manifest import (
    Manifest,
    ManifestEntry,
    load_manifest,
    write_manifest,
)


def test_manifest_round_trip(tmp_path: Path) -> None:
    entry = ManifestEntry(
        collection_key="COLLECTION",
        item_key="ITEM",
        attachment_key="ATTACHMENT",
        source_path="/zotero/source.pdf",
        destination_path="Books/paper.pdf",
        source_size=42,
        source_mtime_ns=123456,
    )
    manifest = Manifest.create(
        collection_key="COLLECTION",
        collection_name="Research",
        items=[entry],
        exported_at=datetime(2026, 7, 12, 10, 30, tzinfo=timezone.utc),
    )
    path = tmp_path / "manifest.json"
    write_manifest(path, manifest)
    loaded = load_manifest(path)
    assert loaded == manifest
    assert path.read_text(encoding="utf-8").endswith("\n")


def test_invalid_manifest_is_ignored(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text("not-json", encoding="utf-8")
    assert load_manifest(path) is None


def test_v1_manifest_is_migrated_in_memory(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "exported_at": "2026-07-12T10:30:00+00:00",
                "collection_key": "COLLECTION",
                "collection_name": "Research",
                "items": [
                    {
                        "collection_key": "COLLECTION",
                        "item_key": "ITEM",
                        "attachment_key": "ATTACHMENT",
                        "source_path": "/zotero/source.pdf",
                        "destination_path": "paper.pdf",
                        "source_size": 42,
                        "source_mtime_ns": 123456,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    manifest = load_manifest(path)
    assert manifest is not None
    assert manifest.version == 4
    assert manifest.filename_template == "author_year_title"
    assert manifest.annotation_layout == "separate"
    assert manifest.items[0].source_sha256 is None
    assert manifest.items[0].state == "active"
