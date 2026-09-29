# ZPM quick start: Zotero links in Emacs

Find a Zotero paper while writing an Org note, insert its link, and jump back to
the paper later. You can also copy links directly from Zotero.

This walkthrough uses **macOS, Zotero 9 or 10, and Emacs Org mode**.
New installation? Follow the [one-time setup](EMACS-SETUP.md) first.

## Find a paper from Emacs

1. **Choose a collection in Zotero.** Select one collection under **My Library**
   and leave Zotero running.
2. **Insert a link.** In your `.org` note, put the cursor where the link belongs.
   Run **M-x zpm-insert-paper-link**, type an author or words from the title,
   and press **Return** to choose a paper.
3. **Jump back to Zotero.** Place the cursor on the inserted link and press
   **C-c C-o** (`org-open-at-point`). Zotero selects that paper's record.

`M-x` means **Alt/Option-x**, or **Escape, then x**, depending on your keyboard
configuration. To cancel the picker, press **C-g**.

**A paper link selects its record; a PDF link opens its PDF.** To go directly to
a PDF, use the copying workflow below and select the PDF attachment.

## Copy a link from Zotero

1. Right-click a paper, PDF attachment, or collection in Zotero.
2. Choose **ZPM → Copy Link → Org**.
3. Paste into your Org note. Open the link with **C-c C-o**.

For a PDF, expand the paper and right-click its PDF row. For Obsidian or another
Markdown editor, choose **Markdown** instead of Org; no Emacs setup is needed.

## Five commands, two to start with

Run these with **M-x**. Start with the first two:

| Command | Use it to… |
| --- | --- |
| **`zpm-insert-paper-link`** | Find a paper and insert its link into your note |
| **`zpm-open-paper`** | Find a paper and select its record in Zotero |
| `zpm-remember-collection` | Keep using one collection for this note; save the note afterward |
| `zpm-forget-collection` | Follow Zotero's current collection again; save the note afterward |
| `zpm-picker-setup` | Show setup help |

![Emacs M-x completion showing the five ZPM commands](images/emacs-zpm-commands.png)

*Shown with Vertico completion. Your Emacs theme and completion list may look different.*

## A few useful details

- A note with a remembered collection uses that collection even when Zotero's
  selection changes. Otherwise, the picker follows the selected collection.
- The picker lists papers directly in the collection. To find a paper in a
  subcollection, select that subcollection. Group libraries are unsupported.
- These links open your local Zotero library; they do not share papers publicly.
- Exporting PDFs is a separate feature. Exports are one-way: edits to exported
  PDFs are not sent back to Zotero and may be overwritten on re-export.

Need more? See [setup and connection help](EMACS-SETUP.md), the
[paper picker reference](PAPER-PICKER.md), or the
[PDF, page, annotation, and multiple-link reference](LINKS.md).
