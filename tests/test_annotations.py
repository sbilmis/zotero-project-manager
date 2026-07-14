from pathlib import Path

from zotero_project_manager.annotations import (
    ANNOTATION_ASSET_MARKER,
    ANNOTATION_MARKER,
    note_html_to_markdown,
    render_annotation_document,
    write_annotation_documents,
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


def test_render_annotation_document_handles_non_text_annotation(tmp_path: Path) -> None:
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
    image = tmp_path / "ANNOT.png"
    image.write_bytes(b"cached-image")
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
        image_path=image,
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
    assert "Paper.assets/ANNOT.png" in document.content
    assert document.images[0].source_path == image
    assert "### Note 1" in document.content
    assert "../../Papers/Paper.pdf" in document.content

    workspace = tmp_path / "workspace"
    write_annotation_documents(workspace, [document])
    exported = workspace / "Annotations" / "Papers" / "Paper.assets" / "ANNOT.png"
    assert exported.read_bytes() == b"cached-image"
    assert exported.parent.joinpath(".zpm-generated").read_text(encoding="utf-8") == (
        ANNOTATION_ASSET_MARKER
    )


def test_render_image_annotation_reports_missing_cache() -> None:
    collection = Collection(1, "COLL", "Research", None, 1)
    attachment = ZoteroAttachment(
        attachment_id=2,
        attachment_key="ATTACH",
        item_id=1,
        item_key="ITEM",
        title="Paper",
        date=None,
        creators=(),
        content_type="application/pdf",
        source_path=None,
        original_path="storage:paper.pdf",
    )
    annotation = ZoteroAnnotation(
        annotation_id=3,
        annotation_key="ANNOT",
        attachment_id=2,
        annotation_type="image",
        text=None,
        comment=None,
        color=None,
        page_label=None,
        sort_index="",
        position="{}",
        author_name=None,
        date_added="",
        date_modified="",
    )
    document = render_annotation_document(
        collection,
        attachment,
        (annotation,),
        (),
        pdf_relative_path=Path("Paper.pdf"),
        annotation_relative_path=Path("Annotations/Paper.md"),
    )
    assert "Image preview is unavailable" in document.content
    assert document.images == ()
