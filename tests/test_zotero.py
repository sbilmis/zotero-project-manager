from pathlib import Path

from zotero_project_manager.zotero import ZoteroDatabase


def test_read_collections_and_resolve_storage_attachment(zotero_fixture: object) -> None:
    fixture = zotero_fixture
    with ZoteroDatabase(fixture.data_dir, database_path=fixture.database) as database:  # type: ignore[attr-defined]
        collections = database.list_collections()
        assert [collection.name for collection in collections] == ["Books", "Claude", "My-AI"]
        attachments = database.attachments_for_collection(2)
        assert len(attachments) == 1
        assert attachments[0].title == "Deep Learning with Python"
        assert attachments[0].creators == ("Chollet",)
        assert attachments[0].source_path == fixture.first_pdf  # type: ignore[attr-defined]


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
