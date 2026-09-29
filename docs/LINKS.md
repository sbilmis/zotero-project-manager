# Zotero link reference

**New to ZPM? Start with the [quick start](QUICKSTART.md).**
See [plugin installation](PLUGIN-QUICKSTART.md#1-install-zpm) and, for Org users,
[Emacs setup](EMACS-SETUP.md).

Zotero Project Manager (ZPM) copies links to collections, paper records, PDFs,
pages, and saved annotations. Use **Org** for Emacs, **Markdown** for Obsidian or
another Markdown editor, and **Zotero URI** for a plain address.

## Copy one collection, paper, or PDF

Right-click one entry in **My Library**, then choose **ZPM → Copy Link → Org**,
**Markdown**, or **Zotero URI**.

| Selected entry | What its link opens |
| --- | --- |
| Collection in the left sidebar | That collection in Zotero |
| Paper record in the middle list | The bibliographic record in My Library |
| PDF attachment beneath a paper, or a standalone PDF | That PDF |

A record contains a paper's title, authors, notes, and attachments. Its link
selects the record without opening a PDF. To copy a PDF link, expand the paper
using its disclosure arrow and right-click the PDF row beneath it.

ZPM supplies the Zotero keys automatically. Notes, non-PDF attachments, group
libraries, deleted entries, and invalid keys cannot produce links. Unsupported
selections disable the command. Copying changes only the clipboard.

## Select a paper inside a particular collection

Open one personal-library collection, right-click a paper directly in it, and
choose **ZPM → Copy Link in This Collection → Org**, **Markdown**, or **Zotero URI**.

This link remembers both the paper and the collection you are viewing. Ordinary
**Copy Link** selects the paper in My Library instead. The Emacs
[paper picker](PAPER-PICKER.md) also inserts collection-specific links.

The collection-specific command is hidden for My Library, saved searches, PDF
attachments, and multiple selected papers or collections. If Zotero shows papers
from subcollections, open the paper's own collection first.

Removing the paper from the collection or deleting the collection may make an
old collection-specific link unavailable. Use ordinary **Copy Link** when you
want a link independent of collection membership.

## Copy several links

Select two or more paper/PDF rows, right-click, and choose **ZPM → Copy Multiple
Links → Org**, **Markdown**, or **Zotero URI**. On macOS, use **Command-click** for
individual rows or **Shift-click** for a range.

The clipboard contains one link per line in Zotero's supplied selection order.
You can mix paper records and PDF attachments; each keeps its own target. A paper
and its PDF produce two links. Attachments are not added implicitly.

If any selected entry is unsupported, copying is disabled. If validation fails,
the previous clipboard is preserved; entries are never silently skipped.
Copying multiple collections, pages, or annotations in one action is unsupported.

## Copy a PDF page or annotation

**ZPM 1.4.0 workaround:** right-clicking a highlight can show an inert **ZPM**
entry. Export its collection using **ZPM → Export → Collection + Annotations**,
then open the generated annotation Markdown and use **Open annotation in
Zotero** beneath that highlight. With the default layout, these files are under
`Annotations/`; Sidecar uses `*.annotations.md` beside the PDF, and Bundle uses
`annotations.md` inside the paper's folder. These links are available for
**My Library** annotations. The direct commands below are fixed in the upcoming
**1.4.1** plugin update.

1. Open a PDF in Zotero's reader.
2. For a page link, right-click text on the page and choose **ZPM → Copy PDF Page
   Link → Org**. Alternatively, select one thumbnail in the reader's
   **Thumbnails** sidebar and right-click it. Use this option if right-clicking
   blank space leaves the page command disabled.
3. For an annotation link, save a highlight or another annotation, then
   right-click it on the page or in the annotations sidebar. Choose
   **ZPM: Copy Annotation Link (Org)**, **(Markdown)**, or **(Zotero URI)**
   directly in the menu. Annotation menus use separate commands because Zotero's
   internal highlight menu does not support nested submenus.

The page submenu also offers **Markdown** and **Zotero URI**. Page numbers refer to
physical PDF positions starting at 1, rather than printed labels such as `iv`.
Annotation links identify a saved annotation and its parent PDF and page. Unsaved
or multiple selected annotations are unsupported. Deleting an annotation may
make its old destination unavailable.

To open these links in Zotero's reader, set **Zotero → Settings → General → Open
PDFs using → Zotero**. PDF links respect this preference.

## Emacs setup on macOS

Load the supplied Org link handlers using the [one-time setup](EMACS-SETUP.md).
Installing the Zotero plugin alone does not install the Emacs code. The handlers
support `zotero-collection:`, `zotero-item:`, and `zotero-pdf:` links. Existing
`zotero:` links supplied by zotxt can remain alongside them.

## Paste, edit the label, and activate

Paste an Org link into your `.org` note. Put the cursor on it and press **C-c C-o**,
or run **M-x org-open-at-point**.

These examples use illustrative keys; copy a real link from your library:

```org
[[zotero-collection:6RIU3F76][Reading list]]
[[zotero-item:ABCD2345][Paper record]]
[[zotero-item:ABCD2345?collection=6RIU3F76][Paper in this collection]]
[[zotero-pdf:EFGH6789][Full PDF]]
[[zotero-pdf:EFGH6789?page=5][PDF page 5]]
[[zotero-pdf:EFGH6789?page=5&annotation=JKLM2345][Saved highlight]]
```

Org normally displays only the label. Use **M-x org-toggle-link-display** to show
its markup; edit the label in `[[destination][label]]` while keeping the
destination unchanged. Keep each link on one logical line. Visual wrapping is
fine; inserting a newline inside a link can break it. ZPM escapes label characters
when copying.

For Obsidian, copy **Markdown**, paste into a note, and click the link in Reading
view:

```markdown
[Paper record](zotero://select/library/items/ABCD2345)
[PDF page 5](zotero://open-pdf/library/items/EFGH6789?page=5)
```

These are desktop links to your Zotero library. They do not publish or share
papers. Another computer needs Zotero and the same synced personal-library
entries; PDF files must also be available locally. Mobile and other note apps
need their own activation support.

## Troubleshooting

- **Menu missing:** confirm ZPM is enabled in **Tools → Plugins**. Update from the
  latest release; Zotero 10 requires ZPM 1.3.2 or newer.
- **Command disabled:** check the selection type. Exclude notes/non-PDF files
  from batches. For a page link, try a single page thumbnail.
- **Org offers a heading menu:** confirm the link handlers are loaded and that
  the link has no hard line breaks. Recopy it if needed.
- **A record or annotation is missing:** check that it still exists in this
  library, that normal Zotero sync has finished, and that any recorded collection
  still contains the paper.
- **An older zotxt link ends in `nil`:** this is a separate bibliography-based
  link. Check your zotxt configuration and reinsert it; ZPM cannot recover a
  missing key in old text.

See [setup troubleshooting](EMACS-SETUP.md#if-something-does-not-work) for Emacs
loading and PDF-opening settings. Developer and manual validation steps live in
[TESTING.md](TESTING.md#links-and-emacs-picker-checks).
