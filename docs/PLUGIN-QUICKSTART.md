# ZPM plugin quick start

Use **Zotero Project Manager (ZPM)** to export a collection into an ordinary
folder or copy links into your notes. The plugin runs inside Zotero;
Python, Homebrew, and Emacs are not required.

## 1. Install ZPM

1. Download the `.xpi` file from the
   [latest release](https://github.com/sbilmis/zotero-project-manager/releases/latest).
   ZPM **1.3.2** supports Zotero **9 and 10.0.x**.
2. In Zotero, open **Tools → Plugins → gear → Install Plugin From File…** and
   select the downloaded file. You can install over an existing ZPM version.
3. Restart if prompted. Confirm **Zotero Project Manager (ZPM)** is enabled.

## 2. Export your first collection

1. Select **one collection** under **My Library**. Make sure its PDFs are
   downloaded and open locally in Zotero.
2. Right-click the collection and choose **ZPM → Export**:

   | Action | What you get |
   | --- | --- |
   | **Collection** | Copies of the collection's PDFs |
   | **Collection + Annotations** | PDFs plus Zotero annotations and child notes as Markdown |

3. Choose a destination folder when prompted. For example, selecting
   `Research/` for a collection named `Reading list` creates
   `Research/Reading list/`. Subcollections are included automatically.
4. The **Export complete** message shows the output path and counts of copied,
   updated, unchanged, and missing files. Open that folder in your file manager
   and use the files in your preferred app.

ZPM remembers the destination. Choose a folder outside Zotero's data directory.
Exports create local files; they do not upload them to another service.

## 3. Update an exported folder

Run the same export again using the same destination. Matching PDFs are skipped;
new or changed PDFs are copied in full. Ordinary exports retain previous copies
of attachments removed from Zotero.

**Exports are one-way: Zotero → folder.** Highlights or edits made to an exported
PDF are not sent back to Zotero and can be overwritten on re-export. Zotero's
annotations are exported as Markdown, not embedded in the copied PDF.

## 4. Copy a link into your notes

Right-click a paper, PDF attachment, or collection and choose
**ZPM → Copy Link → Markdown**, **Org**, or **Zotero URI**. Paste into your note.

- **Markdown:** for Obsidian or another editor that opens `zotero://` links.
- **Org:** for Emacs, with the supplied link handlers installed.
- **Zotero URI:** a plain address for another application's link editor.

A paper link selects its record. To open a PDF directly, expand the paper and
copy the link from its **PDF attachment** row. These links open your local
Zotero library; they do not share the PDF publicly.

See the [Markdown and Org quick start](QUICKSTART.md) for examples and the
optional Emacs paper picker.

## 5. Adjust settings when needed

Right-click a collection → **ZPM → Settings…** to change:

- **Default export folder** and whether to include other attached files.
- **Attachment filename order**, such as Author — Year — Title.
- **Workspace arrangement:** Separate (`Annotations/`), Sidecar (beside each
  PDF), or Bundle (one folder per paper).

Defaults are enough for a first export. Existing workspaces keep their recorded
filename order and layout; use a new export parent folder to try different ones.

**Missing a menu or file?** Check that ZPM is enabled, select one collection,
and confirm its attachments are downloaded. For updates, use **Tools → Plugins →
gear → Check for Updates**. See the [link reference](LINKS.md) for page,
annotation, and multiple-link actions.
