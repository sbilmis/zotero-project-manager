import os
import sqlite3
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
        assert load_manifest(workspace / "manifest.json").items[0].source_sha256  # type: ignore[union-attr]
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


def test_verify_detects_destination_tampering_with_preserved_metadata(
    tmp_path: Path, zotero_fixture: object
) -> None:
    fixture = zotero_fixture
    output = tmp_path / "exports"
    with ZoteroDatabase(fixture.data_dir, database_path=fixture.database) as database:  # type: ignore[attr-defined]
        records = database.list_collections()
        selected = resolve_collection(records, "My-AI")
        forest = build_collection_forest(records)
        CollectionExporter(database, output).export_many([selected], forest)

    destination = output / "My-AI" / "Vaswani - 2017 - Attention Is All You Need.pdf"
    stat = destination.stat()
    destination.write_bytes(b"X" * stat.st_size)
    os.utime(destination, ns=(stat.st_atime_ns, stat.st_mtime_ns))

    with ZoteroDatabase(fixture.data_dir, database_path=fixture.database) as database:  # type: ignore[attr-defined]
        records = database.list_collections()
        stats = CollectionExporter(database, output, verify_hashes=True).export_many(
            [resolve_collection(records, "My-AI")], build_collection_forest(records)
        )[0]
    assert stats.updated == 1
    assert destination.read_bytes() == fixture.second_pdf.read_bytes()  # type: ignore[attr-defined]


def test_prune_deletes_only_hash_verified_removed_file(
    tmp_path: Path, zotero_fixture: object
) -> None:
    fixture = zotero_fixture
    output = tmp_path / "exports"
    _initial_export(output, fixture)
    destination = output / "My-AI" / "Vaswani - 2017 - Attention Is All You Need.pdf"
    _remove_root_item(fixture.database)  # type: ignore[attr-defined]

    with ZoteroDatabase(fixture.data_dir, database_path=fixture.database) as database:  # type: ignore[attr-defined]
        records = database.list_collections()
        stats = CollectionExporter(database, output, prune=True).export_many(
            [resolve_collection(records, "My-AI")], build_collection_forest(records)
        )[0]

    assert stats.removed == 1
    assert stats.pruned == 1
    assert stats.protected == 0
    assert not destination.exists()


def test_prune_dry_run_never_deletes_or_rewrites_manifest(
    tmp_path: Path, zotero_fixture: object
) -> None:
    fixture = zotero_fixture
    output = tmp_path / "exports"
    _initial_export(output, fixture)
    destination = output / "My-AI" / "Vaswani - 2017 - Attention Is All You Need.pdf"
    manifest_path = output / "My-AI" / "manifest.json"
    manifest_before = manifest_path.read_bytes()
    _remove_root_item(fixture.database)  # type: ignore[attr-defined]

    with ZoteroDatabase(fixture.data_dir, database_path=fixture.database) as database:  # type: ignore[attr-defined]
        records = database.list_collections()
        stats = CollectionExporter(database, output, prune=True, dry_run=True).export_many(
            [resolve_collection(records, "My-AI")], build_collection_forest(records)
        )[0]

    assert stats.pruned == 1
    assert destination.is_file()
    assert manifest_path.read_bytes() == manifest_before


def test_first_discovered_attachment_can_be_missing(
    tmp_path: Path, zotero_fixture: object
) -> None:
    fixture = zotero_fixture
    fixture.second_pdf.unlink()  # type: ignore[attr-defined]
    output = tmp_path / "exports"
    stats = _sync_once(output, fixture)
    manifest = load_manifest(output / "My-AI" / "manifest.json")
    assert stats.missing == 1
    assert manifest is not None
    assert any(entry.attachment_key == "ATTACH02" and entry.state == "missing" for entry in manifest.items)


def test_prune_protects_modified_removed_file(tmp_path: Path, zotero_fixture: object) -> None:
    fixture = zotero_fixture
    output = tmp_path / "exports"
    _initial_export(output, fixture)
    destination = output / "My-AI" / "Vaswani - 2017 - Attention Is All You Need.pdf"
    destination.write_bytes(b"user-edited-export")
    _remove_root_item(fixture.database)  # type: ignore[attr-defined]

    with ZoteroDatabase(fixture.data_dir, database_path=fixture.database) as database:  # type: ignore[attr-defined]
        records = database.list_collections()
        stats = CollectionExporter(database, output, prune=True).export_many(
            [resolve_collection(records, "My-AI")], build_collection_forest(records)
        )[0]

    assert stats.pruned == 0
    assert stats.protected == 1
    assert destination.read_bytes() == b"user-edited-export"
    manifest = load_manifest(output / "My-AI" / "manifest.json")
    assert manifest is not None
    assert any(entry.state == "removed" for entry in manifest.items)


def test_readded_identical_attachment_reuses_managed_destination(
    tmp_path: Path, zotero_fixture: object
) -> None:
    fixture = zotero_fixture
    output = tmp_path / "exports"
    _initial_export(output, fixture)
    original_destination = output / "My-AI" / "Vaswani - 2017 - Attention Is All You Need.pdf"
    _remove_root_item(fixture.database)  # type: ignore[attr-defined]
    _sync_once(output, fixture)

    new_source = fixture.data_dir / "storage" / "ATTACH03" / "attention-new.pdf"  # type: ignore[attr-defined]
    new_source.parent.mkdir(parents=True)
    new_source.write_bytes(fixture.second_pdf.read_bytes())  # type: ignore[attr-defined]
    connection = sqlite3.connect(fixture.database)  # type: ignore[attr-defined]
    connection.executemany("INSERT INTO items VALUES (?, ?)", [(300, "ITEM0003"), (301, "ATTACH03")])
    connection.execute("INSERT INTO collectionItems VALUES (?, ?)", (1, 300))
    connection.execute(
        "INSERT INTO itemAttachments VALUES (?, ?, ?, ?)",
        (301, 300, "application/pdf", "storage:attention-new.pdf"),
    )
    connection.commit()
    connection.close()

    stats = _sync_once(output, fixture)
    manifest = load_manifest(output / "My-AI" / "manifest.json")
    assert stats.reconciled == 1
    assert original_destination.is_file()
    assert len(list((output / "My-AI").glob("*.pdf"))) == 1
    assert manifest is not None
    assert any(entry.attachment_key == "ATTACH03" for entry in manifest.items)
    assert not any(entry.attachment_key == "ATTACH02" for entry in manifest.items)


def test_readded_attachment_does_not_reconcile_with_modified_stale_export(
    tmp_path: Path, zotero_fixture: object
) -> None:
    fixture = zotero_fixture
    output = tmp_path / "exports"
    _initial_export(output, fixture)
    stale = output / "My-AI" / "Vaswani - 2017 - Attention Is All You Need.pdf"
    _remove_root_item(fixture.database)  # type: ignore[attr-defined]
    _sync_once(output, fixture)
    stale.write_bytes(b"user-modified-stale-file")

    new_source = fixture.data_dir / "storage" / "ATTACH03" / "attention-new.pdf"  # type: ignore[attr-defined]
    new_source.parent.mkdir(parents=True)
    new_source.write_bytes(fixture.second_pdf.read_bytes())  # type: ignore[attr-defined]
    connection = sqlite3.connect(fixture.database)  # type: ignore[attr-defined]
    connection.executemany("INSERT INTO items VALUES (?, ?)", [(300, "ITEM0003"), (301, "ATTACH03")])
    connection.execute("INSERT INTO collectionItems VALUES (?, ?)", (1, 300))
    connection.execute(
        "INSERT INTO itemAttachments VALUES (?, ?, ?, ?)",
        (301, 300, "application/pdf", "storage:attention-new.pdf"),
    )
    connection.commit()
    connection.close()

    stats = _sync_once(output, fixture)
    assert stats.reconciled == 0
    assert stale.read_bytes() == b"user-modified-stale-file"
    assert len(list((output / "My-AI").glob("*.pdf"))) == 2


def _initial_export(output: Path, fixture: object) -> None:
    _sync_once(output, fixture)


def _sync_once(output: Path, fixture: object):
    with ZoteroDatabase(fixture.data_dir, database_path=fixture.database) as database:  # type: ignore[attr-defined]
        records = database.list_collections()
        return CollectionExporter(database, output).export_many(
            [resolve_collection(records, "My-AI")], build_collection_forest(records)
        )[0]


def _remove_root_item(database_path: Path) -> None:
    connection = sqlite3.connect(database_path)
    connection.execute("DELETE FROM collectionItems WHERE collectionID = 1 AND itemID = 200")
    connection.commit()
    connection.close()
