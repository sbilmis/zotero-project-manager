# Copy Zotero links into notes

This is the **1.2.0 release** of Zotero Project Manager for Zotero
9. The owner verified the consolidated menus and ordinary and collection-specific
Org item activation in the pre2 build.

A **record** is the paper's bibliographic entry: title, authors, publication, notes,
and attachments. A **PDF attachment** is the actual PDF listed beneath that
record (or a standalone PDF). A **collection** is a folder-like entry in Zotero's
left sidebar. A **key** is an eight-character identifier assigned by Zotero, not
a filename or DOI. The plugin finds keys for you. A **URI** is an address that
macOS or another operating system passes to the Zotero application.

## Install or update

1. In Zotero, open **Tools → Plugins**.
2. Click the gear menu, then **Install Plugin From File…**.
3. Choose `dist/zpm-zotero-1.2.0.xpi` in the zotero-project-manager project.
   On this Mac the full path is
   `/Users/sbilmis/developer/projects/zotero-project-manager/dist/zpm-zotero-1.2.0.xpi`.
4. Follow Zotero's prompts; restart Zotero if requested. Confirm that **Zotero
   Project Manager** shows version **1.2.0**.
5. To open PDFs in Zotero's own reader, open **Zotero → Settings → General** and
   set the **Open PDFs using** field to **Zotero**. The `open-pdf` URI respects this
   preference; it cannot force Zotero's reader when an external reader is selected.

An XPI is the installable plugin file. Python, Actions & Tags, zotxt, and a
bibliography style are not required for copying. Existing export
commands continue to work independently. Copying only changes the clipboard:
there are no export prompts, files, library edits, shell processes, or uploads.

## Copy one collection, paper, or PDF

In Zotero, use entries in **My Library**. Right-click one entry, then choose
**Zotero Project Manager → Copy Link → Org**, **Markdown**, or **Zotero URI**.
Org is for Emacs; Markdown is for Obsidian; Zotero URI copies only the address
for another application's link editor. The selected entry determines the target:

| Selected entry | Activation result |
| --- | --- |
| Collection in the left sidebar | Selects the collection |
| Paper record in the middle list | Selects the record in My Library, without opening a PDF |
| PDF attachment in the middle list | Opens that particular PDF |

To select a PDF attachment, click the disclosure arrow beside its parent paper
and right-click the PDF row beneath it. Its key differs from the paper's key.
Standalone PDF attachments work too. Unsupported entries disable Copy Link;
there are no redundant Item/PDF commands to choose between.

The collection menu now has one parent:

```text
Zotero Project Manager
    Copy Link
        Org
        Markdown
        Zotero URI
    Export
        Collection
        Collection + Annotations
    Settings…
```

The export actions and Settings retain their existing behavior. Export appears
on the collection menu; paper/PDF menus contain only the applicable link actions.
Group libraries, notes, non-PDF attachments, deleted entries, and invalid/missing
keys cannot produce links. Single-link copying is hidden for multiple selections.

## Select a paper inside the collection you copied from

In Zotero's left sidebar, open a collection such as **scientometry**. Right-click
one paper directly in that collection, then choose **Zotero Project Manager →
Copy Link in This Collection → Org**, **Markdown**, or **Zotero URI**.

The link records both the paper key and the currently selected collection key.
A paper can belong to many collections; this command remembers the one you are
viewing without choosing among the others. It does not open the paper's PDF.
For example (replace illustrative keys by copying a real link):

```org
Read [[zotero-item:ABCD2345?collection=6RIU3F76][this paper in scientometry]].
```

```markdown
Read [this paper in scientometry](zotero://select/library/collections/6RIU3F76/items/ABCD2345).
```

The command appears only for a single paper directly belonging to the selected
personal-library collection. It is hidden in My Library, saved searches, PDF
selections, and batches. If Zotero is showing items from subcollections, open
the paper's own collection first. Validation runs again when the command is used.

Ordinary **Copy Link** remains unchanged and selects the paper in My Library.
Previously copied links keep working. Collection-specific links may stop working
if you remove the paper from that collection or delete the collection; use the
ordinary link when you want it independent of collection membership. No automatic
fallback or guessing is performed. PDF/page/annotation links still open the reader.

## Copy several links

In Zotero's middle item list, select two or more rows using Command-click on
macOS, or select a contiguous range with Shift-click. Right-click the selection,
then choose **Zotero Project Manager → Copy Multiple Links → Org**, **Markdown**,
or **Zotero URI**.

The clipboard contains one link per line in Zotero's supplied selection order.
A selection may mix paper records and PDF attachments: each keeps its own target.
Including both a paper and its PDF produces two different links. No attachments
are added implicitly. If any entry is unsupported or invalid, the command is
disabled; if validation fails when clicked, an error appears and the previous
clipboard remains unchanged. No entries are silently skipped. Multi-collection,
multiple-page, and multiple-annotation copying are not supported.

## Copy a PDF page or annotation

1. Open a PDF inside Zotero's reader.
2. For a page link, right-click text on the desired PDF page and choose **Zotero Project Manager → Copy PDF Page Link → Org**. Alternatively, open the reader's
   left sidebar, choose its **Thumbnails** view (small page previews), select one
   thumbnail and right-click it. This is the reliable option if clicking blank
   space provides no page position and the command is disabled.
3. For an annotation link, first save a highlight or another annotation normally
   in Zotero. Right-click that annotation on the page or in the reader's
   annotations sidebar. Choose **Zotero Project Manager → Copy Annotation Link → Org**.
4. The same reader submenus offer **Markdown** and **Zotero URI** formats.

Page numbers are physical PDF positions, starting at 1, not printed page labels
such as `iv` or `123`. Annotation links identify the saved annotation as well as
its parent PDF and physical page. Unsaved/unavailable annotations, annotations
from another PDF, and multiple selected annotations are rejected. Deleting an
annotation later can make its annotation destination unavailable.

## Emacs setup on macOS

Org mode edits `.org` files. Its links have a **destination** and a **visible
label**: `[[destination][label]]`. A handler is a small Emacs Lisp function that
opens a destination when you activate the link.

On sbilmis the managed file is:

```text
~/developer/projects/my_config/home/private_dot_emacs.d/private_lisp/init-org.el
```

The live file Emacs loads is `~/.emacs.d/lisp/init-org.el`. ChezMoi manages the
relationship between these files. `~` means your home directory. The changes
are already installed in both files on sbilmis and active in running Emacs.
No changes were made on neumann.

For recovery or another Mac:

1. In Emacs run **M-x find-file** and open the managed source path above. `M-x`
   means Option-x, or Escape followed by x; type the command and press Return.
2. Find the existing `sb/org-open-zotero-collection` function and its adjacent
   `with-eval-after-load 'org` registration. Replace that section with the forms
   in [zpm-org-links.el](emacs/zpm-org-links.el), from `defun sb/org-zotero-key`
   through the end of `with-eval-after-load`. Do not add a second copy. The block
   belongs after `use-package zotxt` and before `use-package emojify`.
3. Preserve the existing `use-package zotxt` block, its APA style setting, and
   the existing `zotero:` registration provided by org-zotxt. Save the edited
   source with **M-x save-buffer**.
4. Open macOS **Terminal** and run each command below. Review the diff: it should
   contain only the intended link functions and registrations. Apply this one
   file, not the entire configuration.

```sh
chezmoi diff ~/.emacs.d/lisp/init-org.el
chezmoi apply ~/.emacs.d/lisp/init-org.el
chezmoi verify ~/.emacs.d/lisp/init-org.el
```

5. In Emacs select only the five affected top-level forms (four `defun` forms
   and the `with-eval-after-load` form), then run **M-x eval-region**. Do not
   evaluate the whole `init-org.el` module. You can select the text with the mouse.
   Alternatively restart Emacs after applying. The existing `init.el` loads
   `init-org`, so registration persists across startup and waits until Org loads.
6. With an Org buffer open, use **M-x eval-expression** to check:

```elisp
(org-link-get-parameter "zotero-item" :follow)
(org-link-get-parameter "zotero-pdf" :follow)
```

Evaluate one expression at a time. Expect `sb/org-open-zotero-item` and
`sb/org-open-zotero-pdf`. No new keybindings are added.

The handlers validate destinations and call `start-process` with `/usr/bin/open`
and exactly one separate URI argument, without a shell. The item handler accepts a key or `KEY?collection=KEY`. The PDF handler accepts
only a key, `KEY?page=N`, or `KEY?page=N&annotation=KEY`. Existing valid
`zotero-collection:` links retain the same destination.

## Paste, edit the label, and activate

In an Emacs `.org` note, paste normally or run **M-x yank**. These are illustrative
keys; copy your real links from Zotero for testing:

```org
For context, see [[zotero-collection:6RIU3F76][scientometry]].
I should reread [[zotero-item:ABCD2345][this paper]] before writing the introduction.
The details are in [[zotero-pdf:EFGH6789][the full PDF]].
Compare [[zotero-pdf:EFGH6789?page=5][PDF page 5]] with my notes.
Review [[zotero-pdf:EFGH6789?page=5&annotation=JKLM2345][this highlight]].
```

Org normally displays only the label. Put the cursor on the link and run
**M-x org-open-at-point** (the existing `C-c C-o` command also works). An item
link selects the record; expand its attachments or double-click a PDF when you
want to read it. A PDF link goes directly to that attachment.

To change the visible words, run **M-x org-toggle-link-display** to show the
markup. Change only the text between the second `[` and the final `]]`, such as
`this paper` or `this highlight`. Keep the destination unchanged. Save with
**M-x save-buffer**, and toggle link display again if desired.

Keep each link on one logical line: visual wrapping at the window edge is fine;
pressing Return inside a link is not. The plugin replaces hard newlines with
spaces and square brackets in labels with fullwidth `［ ］`, preventing broken
Org syntax. Markdown punctuation in labels is escaped too.

For Obsidian, paste the Markdown version into a note:

```markdown
I should reread [this paper](zotero://select/library/items/ABCD2345).
Compare [PDF page 5](zotero://open-pdf/library/items/EFGH6789?page=5).
```

Switch the note to Reading view and click the link. In Markdown source, edit
only the label inside the first square brackets. If the application asks whether
to open Zotero, allow that for the link you intend to open. These are desktop
Zotero links, not public web links or shared PDFs. Another computer needs Zotero
and the same synced personal-library entries; PDF files must also be available.
Mobile and other note apps require their own activation checks.

## Troubleshooting and manual acceptance checks

- **Copy menu missing:** check the installed plugin version in Zotero's **Tools
  → Plugins**, and restart Zotero if installation requested it.
- **Command disabled:** select the correct type in My Library. For batches,
  exclude notes and non-PDF files. For page links, use a single page thumbnail.
- **Error while copying:** read **Cannot copy Zotero link**. Nothing replaces the
  previous clipboard on validation failure; correct the selection and copy again.
- **PDF opens externally:** set **Settings → General → Open PDFs using → Zotero**.
- **Org offers a heading menu:** confirm the handlers above are registered and
  remove hard/blank lines from inside the link. Recopy the link if uncertain.
- **A Zotero item is missing:** confirm the key's library exists on this computer
  and finish normal sync. The plugin validates key syntax, not future availability.
- **Old zotxt link ends in `nil`:** retain installed APA as
  `zotxt-default-bibliography-style`, then delete and reinsert the broken zotxt
  link. Native copying never uses bibliography generation and cannot repair
  a missing key in old text. Keep your existing zotxt instructions and setup.

After installing the release, test one real collection, paper, paper-in-collection, PDF, physical
page, and saved annotation in Emacs. Test the Markdown equivalents in Obsidian.
Try a mixed paper/PDF batch and confirm two links, then include a note and
confirm copying is disabled. Test a group-library entry and a non-PDF attachment.
Finally perform an existing export into a disposable test folder to confirm the
usual export dialog/results. Installation and these GUI checks remain manual;
automated tests use simulated Zotero API objects and do not install the XPI.

## Developer checks and sources

From the repository directory in Terminal:

```sh
node --check zotero-plugin/links.js
node --test zotero-plugin/tests/*.test.cjs
emacs --batch -Q -l zotero-plugin/tests/org-links.test.el
ZPM_ORG_CONFIG="$HOME/developer/projects/my_config/home/private_dot_emacs.d/private_lisp/init-org.el" emacs --batch -Q -l zotero-plugin/tests/org-links.test.el
.venv/bin/python -m pytest
python3 scripts/build_zotero_plugin.py --development
unzip -t dist/zpm-zotero-1.2.0.xpi
```

The ERT tests run on macOS, exercise real Org activation with process calls
stubbed, and check deferred registration, malformed destinations, and preservation
of the `zotero:` handler. Node tests cover formats, escaping, keys, selection
validation, atomic batches, reader hooks, clipboard dispatch, and cleanup.
The XPI contains `links.js`, loaded before the plugin starts. CI and release
builds verify the exact XPI hash in the update feed.

Verified against current Zotero source and the installed Zotero application:

- [URI routing for collections/items/PDFs and page/annotation parameters](https://github.com/zotero/zotero/blob/main/chrome/content/zotero/ZoteroProtocolHandler.mjs)
- [Reader context-menu event API](https://github.com/zotero/zotero/blob/main/chrome/content/zotero/xpcom/reader.js)
- [PDF-opening preferences and reader dispatch](https://github.com/zotero/zotero/blob/main/chrome/content/zotero/xpcom/fileHandlers.js)
- [Key alphabet and validation](https://github.com/zotero/utilities/blob/master/utilities.js)
- [Native plain-text clipboard API](https://github.com/zotero/zotero/blob/main/chrome/content/zotero/xpcom/utilities_internal.js)
