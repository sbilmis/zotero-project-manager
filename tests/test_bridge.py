from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from zotero_project_manager.bridge import BridgeError, BridgeSource
from zotero_project_manager.cli import app


runner = CliRunner()


def bridge_payload(zotero_fixture: object) -> dict[str, object]:
    fixture = zotero_fixture
    return {
        "schema_version": 1,
        "zotero_version": "9.0.6",
        "data_dir": str(fixture.data_dir),  # type: ignore[attr-defined]
        "collections": [
            {"id": 1, "key": "ROOTKEY1", "name": "My-AI", "parent_id": None, "library_id": 1},
            {"id": 2, "key": "BOOKKEY1", "name": "Books", "parent_id": 1, "library_id": 1},
        ],
        "attachments": {
            "1": [],
            "2": [
                {
                    "attachment_id": 101,
                    "attachment_key": "ATTACH01",
                    "item_id": 100,
                    "item_key": "ITEM0001",
                    "title": "Deep Learning with Python",
                    "date": "2021",
                    "creators": ["Chollet"],
                    "content_type": "application/pdf",
                    "source_path": str(fixture.first_pdf),  # type: ignore[attr-defined]
                    "original_path": "storage:deep-learning.pdf",
                    "doi": None,
                    "tags": ["Book"],
                }
            ],
        },
        "annotations": {
            "101": [
                {
                    "annotation_id": 102,
                    "annotation_key": "ANNOT001",
                    "attachment_id": 101,
                    "annotation_type": "highlight",
                    "text": "Neural networks learn useful representations.",
                    "comment": "Connect this to the current model.",
                    "color": "#ffd400",
                    "page_label": "4",
                    "sort_index": "00003|000001|00000",
                    "position": '{"pageIndex": 3}',
                    "author_name": "Selcuk",
                    "date_added": "2026-07-01 10:00:00",
                    "date_modified": "2026-07-02 11:00:00",
                    "tags": ["Important"],
                    "image_path": None,
                }
            ]
        },
        "notes": {
            "100": [
                {
                    "note_id": 103,
                    "note_key": "NOTE0001",
                    "parent_item_id": 100,
                    "title": "Reading notes",
                    "content": "<p>Key idea</p>",
                    "date_added": "2026-07-01 10:00:00",
                    "date_modified": "2026-07-02 11:00:00",
                    "tags": ["Research note"],
                }
            ]
        },
    }


def test_bridge_source_loads_models(tmp_path: Path, zotero_fixture: object) -> None:
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(bridge_payload(zotero_fixture)), encoding="utf-8")
    source = BridgeSource.load(path)
    assert source.zotero_version == "9.0.6"
    assert source.list_collections()[1].key == "BOOKKEY1"
    assert source.attachments_for_collection(2)[0].source_path == zotero_fixture.first_pdf  # type: ignore[attr-defined]
    assert source.annotations_for_attachment(101)[0].annotation_type == "highlight"
    assert source.child_notes_for_item(100)[0].title == "Reading notes"


def test_plugin_export_uses_snapshot_without_opening_sqlite(
    tmp_path: Path, zotero_fixture: object
) -> None:
    image = zotero_fixture.data_dir / "cache" / "library" / "ANNOT001.png"  # type: ignore[attr-defined]
    image.parent.mkdir(parents=True)
    image.write_bytes(b"cached-image")
    payload = bridge_payload(zotero_fixture)
    payload["annotations"]["101"][0]["annotation_type"] = "image"  # type: ignore[index]
    payload["annotations"]["101"][0]["image_path"] = str(image)  # type: ignore[index]
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    output = tmp_path / "exports"
    result = runner.invoke(
        app,
        [
            "plugin-export",
            str(path),
            "ROOTKEY1",
            "--output",
            str(output),
            "--annotations",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Zotero 9.0.6 companion snapshot exported" in result.output
    assert (output / "My-AI" / "Books" / "Chollet - 2021 - Deep Learning with Python.pdf").is_file()
    assert (
        output
        / "My-AI"
        / "Annotations"
        / "Books"
        / "Chollet - 2021 - Deep Learning with Python.md"
    ).is_file()
    assert (
        output
        / "My-AI"
        / "Annotations"
        / "Books"
        / "Chollet - 2021 - Deep Learning with Python.assets"
        / "ANNOT001.png"
    ).read_bytes() == b"cached-image"


def test_bridge_rejects_unknown_schema(tmp_path: Path, zotero_fixture: object) -> None:
    payload = bridge_payload(zotero_fixture)
    payload["schema_version"] = 99
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(BridgeError, match="Unsupported plugin snapshot schema"):
        BridgeSource.load(path)


def test_bridge_accepts_annotation_png_inside_zotero_cache(
    tmp_path: Path, zotero_fixture: object
) -> None:
    payload = bridge_payload(zotero_fixture)
    image = zotero_fixture.data_dir / "cache" / "library" / "ANNOT001.png"  # type: ignore[attr-defined]
    image.parent.mkdir(parents=True)
    image.write_bytes(b"image")
    payload["annotations"]["101"][0]["annotation_type"] = "image"  # type: ignore[index]
    payload["annotations"]["101"][0]["image_path"] = str(image)  # type: ignore[index]
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    source = BridgeSource.load(path)
    assert source.annotations_for_attachment(101)[0].image_path == image


def test_bridge_rejects_annotation_image_outside_zotero_cache(
    tmp_path: Path, zotero_fixture: object
) -> None:
    payload = bridge_payload(zotero_fixture)
    image = tmp_path / "outside.png"
    image.write_bytes(b"image")
    payload["annotations"]["101"][0]["image_path"] = str(image)  # type: ignore[index]
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(BridgeError, match="inside Zotero's cache"):
        BridgeSource.load(path)
