from pathlib import Path

from zotero_project_manager.annotations import (
    ANNOTATION_MARKER,
    note_html_to_markdown,
    render_annotation_document,
)
from zotero_project_manager.models import (
    Collection,
    ZoteroAnnotation,
    ZoteroAttachment,
    ZoteroNote,
)


def test_note_html_to_markdown_preserves_blocks_and_lists() -> None:
    value = "<div><p>First &amp; second</p><ul><li>One</li><li>Two</li></ul></div>"
    assert note_html_to_markdown(value) == "First & second\n\n- One\n\n- Two"


def test_render_annotation_document_handles_non_text_annotation() -> None:
    collection = Collection(1, "COLL", "Research", None, 1)
    attachment = ZoteroAttachment(
        attachment_id=2,
        attachment_key="ATTACH",
        item_id=1,
        item_key="ITEM",
        title="Paper",
        date="2025",
        creators=("Curie",),
        content_type="application/pdf",
        source_path=Path("paper.pdf"),
        original_path="storage:paper.pdf",
    )
    annotation = ZoteroAnnotation(
        annotation_id=3,
        annotation_key="ANNOT",
        attachment_id=2,
        annotation_type="image",
        text=None,
        comment="Inspect this figure.",
        color="#ff0000",
        page_label="8",
        sort_index="00007",
        position='{"pageIndex":7}',
        author_name=None,
        date_added="2026-01-01",
        date_modified="2026-01-02",
    )
    note = ZoteroNote(
        note_id=4,
        note_key="NOTE",
        parent_item_id=1,
        title=None,
        content="<p>Related note</p>",
        date_added="2026-01-01",
        date_modified="2026-01-02",
    )
    document = render_annotation_document(
        collection,
        attachment,
        (annotation,),
        (note,),
        pdf_relative_path=Path("Papers/Paper.pdf"),
        annotation_relative_path=Path("Annotations/Papers/Paper.md"),
    )
    assert document.content.startswith(ANNOTATION_MARKER)
    assert "Page 8 — Image" in document.content
    assert "Inspect this figure." in document.content
    assert "### Note 1" in document.content
    assert "../../Papers/Paper.pdf" in document.content
