import os
from pathlib import Path

import pytest

from zotero_project_manager.collections import build_collection_forest, resolve_collection
from zotero_project_manager.exporter import CollectionExporter, ExportError
from zotero_project_manager.manifest import load_manifest
from zotero_project_manager.zotero import ZoteroDatabase


def test_recursive_export_and_incremental_update(tmp_path: Path, zotero_fixture: object) -> None:
    fixture = zotero_fixture
    output = tmp_path / "exports"
    with ZoteroDatabase(fixture.data_dir, database_path=fixture.database) as database:  # type: ignore[attr-defined]
        records = database.list_collections()
        forest = build_collection_forest(records)
        selected = resolve_collection(records, "My-AI")
        exporter = CollectionExporter(database, output)

        first = exporter.export_many([selected], forest)[0]
        assert first.copied == 2
        assert first.unchanged == 0
        workspace = output / "My-AI"
        assert (workspace / "Vaswani - 2017 - Attention Is All You Need.pdf").is_file()
        assert (workspace / "Books" / "Chollet - 2021 - Deep Learning with Python.pdf").is_file()

        second = exporter.export_many([selected], forest)[0]
        assert second.unchanged == 2
        assert second.copied == 0

        fixture.first_pdf.write_bytes(b"changed-content")  # type: ignore[attr-defined]
        os.utime(fixture.first_pdf, None)  # type: ignore[attr-defined]
        third = exporter.export_many([selected], forest)[0]
        assert third.updated == 1
        assert third.unchanged == 1
        assert len(load_manifest(workspace / "manifest.json").items) == 2  # type: ignore[union-attr]
        assert "PDF count: 2" in (workspace / "README.md").read_text(encoding="utf-8")


def test_dry_run_writes_nothing(tmp_path: Path, zotero_fixture: object) -> None:
    fixture = zotero_fixture
    output = tmp_path / "exports"
    with ZoteroDatabase(fixture.data_dir, database_path=fixture.database) as database:  # type: ignore[attr-defined]
        records = database.list_collections()
        stats = CollectionExporter(database, output, dry_run=True).export_many(
            [resolve_collection(records, "My-AI")], build_collection_forest(records)
        )[0]
    assert stats.copied == 2
    assert not output.exists()


def test_refuses_output_inside_zotero(zotero_fixture: object) -> None:
    fixture = zotero_fixture
    with ZoteroDatabase(fixture.data_dir, database_path=fixture.database) as database:  # type: ignore[attr-defined]
        with pytest.raises(ExportError):
            CollectionExporter(database, fixture.data_dir / "exports")  # type: ignore[attr-defined]


def test_unmanaged_workspace_requires_overwrite(tmp_path: Path, zotero_fixture: object) -> None:
    fixture = zotero_fixture
    output = tmp_path / "exports"
    (output / "My-AI").mkdir(parents=True)
    with ZoteroDatabase(fixture.data_dir, database_path=fixture.database) as database:  # type: ignore[attr-defined]
        records = database.list_collections()
        exporter = CollectionExporter(database, output)
        with pytest.raises(ExportError, match="not managed"):
            exporter.export_many(
                [resolve_collection(records, "My-AI")], build_collection_forest(records)
            )


def test_missing_source_keeps_prior_manifest_entry(
    tmp_path: Path, zotero_fixture: object
) -> None:
    fixture = zotero_fixture
    output = tmp_path / "exports"
    with ZoteroDatabase(fixture.data_dir, database_path=fixture.database) as database:  # type: ignore[attr-defined]
        records = database.list_collections()
        exporter = CollectionExporter(database, output)
        selected = resolve_collection(records, "My-AI")
        forest = build_collection_forest(records)
        exporter.export_many([selected], forest)
        fixture.first_pdf.unlink()  # type: ignore[attr-defined]
        stats = exporter.export_many([selected], forest)[0]

    manifest = load_manifest(output / "My-AI" / "manifest.json")
    assert stats.missing == 1
    assert manifest is not None
    assert len(manifest.items) == 2


def test_rejects_collection_directory_symlink_escape(
    tmp_path: Path, zotero_fixture: object
) -> None:
    fixture = zotero_fixture
    output = tmp_path / "exports"
    workspace = output / "My-AI"
    workspace.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (workspace / "Books").symlink_to(outside, target_is_directory=True)
    with ZoteroDatabase(fixture.data_dir, database_path=fixture.database) as database:  # type: ignore[attr-defined]
        records = database.list_collections()
        exporter = CollectionExporter(database, output, overwrite=True)
        with pytest.raises(ExportError, match="outside the workspace"):
            exporter.export_many(
                [resolve_collection(records, "My-AI")], build_collection_forest(records)
            )
