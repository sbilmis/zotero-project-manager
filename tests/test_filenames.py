from pathlib import Path

import pytest

from zotero_project_manager.filenames import (
    attachment_filename,
    choose_available_name,
    sanitize_component,
    validate_filename_template,
)
from zotero_project_manager.models import ZoteroAttachment


def make_attachment(**overrides: object) -> ZoteroAttachment:
    values: dict[str, object] = {
        "attachment_id": 2,
        "attachment_key": "ATTACH01",
        "item_id": 1,
        "item_key": "ITEM0001",
        "title": "A title: with / illegal? characters",
        "date": "Issued 2024-03",
        "creators": ("Curie",),
        "content_type": "application/pdf",
        "source_path": Path("paper.PDF"),
        "original_path": "storage:paper.PDF",
    }
    values.update(overrides)
    return ZoteroAttachment(**values)  # type: ignore[arg-type]


def test_attachment_filename_uses_metadata_and_sanitizes() -> None:
    assert attachment_filename(make_attachment()) == (
        "Curie - 2024 - A title- with - illegal- characters.pdf"
    )


def test_attachment_filename_gracefully_falls_back() -> None:
    result = attachment_filename(
        make_attachment(title=None, date=None, creators=(), source_path=Path("notes.pdf"))
    )
    assert result == "notes.pdf"


def test_attachment_filename_does_not_duplicate_extension_in_title() -> None:
    result = attachment_filename(
        make_attachment(title="main_notes.pdf", date=None, creators=(), source_path=Path("main.pdf"))
    )
    assert result == "main_notes.pdf"


def test_attachment_filename_supports_named_metadata_orders() -> None:
    attachment = make_attachment(title="A Paper", date="2024", creators=("Curie",))
    assert attachment_filename(attachment, "author_year_title") == "Curie - 2024 - A Paper.pdf"
    assert attachment_filename(attachment, "author_title_year") == "Curie - A Paper - 2024.pdf"
    assert attachment_filename(attachment, "year_author_title") == "2024 - Curie - A Paper.pdf"
    assert attachment_filename(attachment, "year_title_author") == "2024 - A Paper - Curie.pdf"
    assert attachment_filename(attachment, "title_author_year") == "A Paper - Curie - 2024.pdf"
    assert attachment_filename(attachment, "title_year_author") == "A Paper - 2024 - Curie.pdf"
    assert attachment_filename(attachment, "author_title") == "Curie - A Paper.pdf"
    assert attachment_filename(attachment, "year_title") == "2024 - A Paper.pdf"
    assert attachment_filename(attachment, "title_author") == "A Paper - Curie.pdf"
    assert attachment_filename(attachment, "title_year") == "A Paper - 2024.pdf"
    assert attachment_filename(attachment, "title") == "A Paper.pdf"


def test_invalid_filename_template_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown filename template"):
        validate_filename_template("author-title-random")


def test_sanitize_reserved_and_blank_names() -> None:
    assert sanitize_component("CON") == "_CON"
    assert sanitize_component(" ... ") == "Untitled"


def test_duplicate_names_prefer_stable_attachment_key() -> None:
    reserved: set[str] = set()
    assert choose_available_name("Paper.pdf", reserved, key="AAA") == "Paper.pdf"
    assert choose_available_name("Paper.pdf", reserved, key="BBB") == "Paper [BBB].pdf"
