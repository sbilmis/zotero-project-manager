from pathlib import Path

import sqlite3

import pytest

from zotero_project_manager.zotero import ZoteroDatabase, ZoteroDatabaseError


def test_read_collections_and_resolve_storage_attachment(zotero_fixture: object) -> None:
    fixture = zotero_fixture
    with ZoteroDatabase(fixture.data_dir, database_path=fixture.database) as database:  # type: ignore[attr-defined]
        collections = database.list_collections()
        assert [collection.name for collection in collections] == ["Books", "Claude", "My-AI"]
        attachments = database.attachments_for_collection(2)
        assert len(attachments) == 1
        assert attachments[0].title == "Deep Learning with Python"
        assert attachments[0].creators == ("Chollet",)
        assert attachments[0].doi is None
        assert attachments[0].tags == ("Book",)
        assert attachments[0].source_path == fixture.first_pdf  # type: ignore[attr-defined]

        root_attachment = database.attachments_for_collection(1)[0]
        assert root_attachment.doi == "10.5555/attention"
        assert root_attachment.tags == ("AI",)

        annotations = database.annotations_for_attachment(101)
        assert len(annotations) == 1
        assert annotations[0].annotation_type == "highlight"
        assert annotations[0].page_label == "4"
        assert annotations[0].tags == ("Important",)

        notes = database.child_notes_for_item(100, attachment_id=101)
        assert len(notes) == 1
        assert notes[0].title == "Reading notes"
        assert notes[0].tags == ("Research note",)


def test_relative_link_requires_explicit_base(tmp_path: Path, zotero_fixture: object) -> None:
    fixture = zotero_fixture
    linked = tmp_path / "linked"
    with ZoteroDatabase(
        fixture.data_dir,  # type: ignore[attr-defined]
        database_path=fixture.database,  # type: ignore[attr-defined]
        linked_attachment_base_dir=linked,
    ) as database:
        assert database.resolve_attachment_path("attachments:folder/paper.pdf", "KEY") == (
            linked / "folder" / "paper.pdf"
        ).resolve()


def test_image_annotation_uses_existing_read_only_cache(zotero_fixture: object) -> None:
    fixture = zotero_fixture
    image = fixture.data_dir / "cache" / "library" / "ANNOT001.png"  # type: ignore[attr-defined]
    image.parent.mkdir(parents=True)
    image.write_bytes(b"cached-annotation")
    connection = sqlite3.connect(fixture.database)  # type: ignore[attr-defined]
    connection.execute("UPDATE itemAnnotations SET type = 3 WHERE itemID = 102")
    connection.commit()
    connection.close()

    with ZoteroDatabase(
        fixture.data_dir, database_path=fixture.database  # type: ignore[attr-defined]
    ) as database:
        annotation = database.annotations_for_attachment(101)[0]

    assert annotation.annotation_type == "image"
    assert annotation.image_path == image


def test_locked_database_error_explains_how_to_retry(zotero_fixture: object) -> None:
    fixture = zotero_fixture
    database = ZoteroDatabase(fixture.data_dir, database_path=fixture.database)  # type: ignore[attr-defined]
    database.open()
    database.connection.execute("PRAGMA busy_timeout = 1")
    blocker = sqlite3.connect(fixture.database)  # type: ignore[attr-defined]
    blocker.execute("BEGIN EXCLUSIVE")
    try:
        with pytest.raises(ZoteroDatabaseError) as error:
            database.list_collections()
    finally:
        blocker.rollback()
        blocker.close()
        database.close()

    message = str(error.value)
    assert "temporarily locked" in message
    assert "close Zotero" in message
    assert "read-only access" in message
    assert "made no changes" in message
