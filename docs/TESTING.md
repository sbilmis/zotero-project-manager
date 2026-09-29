# Test the simplified exporter with Agentic_AI

This guide targets Zotero plugin **1.4.0**, compatible with Zotero 9 and 10.0.x. It exports to one standard workspace
per collection, with no Gemini Notebook or DEVONthink integration. Existing export
folders are not removed by upgrading.

## 1. Install or update the stable release

1. For a published release, existing users can run **Tools → Plugins → gear → Check for Updates**.
   For a local build, use the XPI from this checkout; it is not offered by Check for Updates until published.
   For a manual install, download `zpm-zotero-1.4.0.xpi` from the
   [1.4.0 release](https://github.com/sbilmis/zotero-project-manager/releases/tag/v1.4.0).
   To test multi-collection export, build `dist/zpm-zotero-1.4.0.xpi` from this checkout:

   ```bash
   python3 scripts/build_zotero_plugin.py
   ```

2. In Zotero, open **Tools → Plugins → gear → Install Plugin From File…** and
   select the XPI. Install over the existing plugin; no uninstall is needed.
3. Restart Zotero if requested and confirm the intended ZPM version is enabled.
4. Right-click **Agentic_AI**, then open **ZPM → Export**. Expect:

   - **Collection**
   - **Collection + Annotations**

   **Settings…** is beside Export in the parent ZPM menu.

   The Gemini/DT4 Send actions and notebook-link setup must be gone.

Add-on Market may temporarily show 1.0.0 until its catalog/mirror refreshes. Do
not use Reinstall while it lists the older version; use Zotero's Check for Updates
or the direct release XPI instead. No uninstall is needed, including from pre5.

## 2. Confirm Settings / Choose still works

1. Open **Settings…**. Your saved export parent folder should appear.
2. Click **Choose…**. A native folder-selection dialog should open attached to
   Settings. Cancel once and confirm the path stays unchanged.
3. Select your intended permanent parent folder, such as your existing
   `/Users/sbilmis/scratch/zpm_test`. Expect **Export folder saved.**
4. Close and reopen Settings to verify the path persists. Do not use Zotero's
   data/storage directory as the export parent.
5. Leave layout and filename choices unchanged for an existing workspace; those
   workspaces retain their recorded settings. Test different layouts in a new
   parent folder only if you deliberately want another workspace.

## 3. Export the selected collection

1. Confirm a few PDFs inside **Agentic_AI** open locally in Zotero.
2. Right-click **Agentic_AI → ZPM → Export → Collection + Annotations**.
3. Expect an **Export complete** summary and the path
   `/Users/sbilmis/scratch/zpm_test/Agentic_AI` if you selected that parent folder.
4. Open that folder in Finder yourself. Check PDFs, generated annotation/child-note
   Markdown, and any selected non-PDF attachments. Their placement follows the
   workspace layout: `Annotations/`, sidecars, or per-paper bundles.
5. No browser, Notebook, DT4, AppleScript prompt, or automatic upload should occur.
   No new `Agentic_AI - NotebookLM` workspace should be created.

Selecting Agentic_AI directly includes its descendants, not its My-AI parent or siblings.
**Collection** uses the same workspace without generating new annotation
documents; previously exported files can remain, since ordinary exports do not prune.

## 4. Check repeat export and existing-folder preservation

1. Use a fresh test export containing no personal PDF edits. Re-export Agentic_AI with the same action. Unchanged PDFs should be counted as
   unchanged, with no app-specific duplicate workspace created.
2. If an old `Agentic_AI - NotebookLM` folder already exists, it will still exist.
   The upgrade and standard export do not delete or update it; that is intentional.
3. Restart Zotero and confirm Settings and the simplified menu remain correct.
4. If using the files elsewhere, open that app yourself and select only the files
   you want. Keep hidden `.zpm/` bookkeeping out of imports/uploads. Choose file
   types the destination accepts. zpm does not manage external copies or sources.

No cleanup of old exported folders, Google notebooks, or DT4 records is performed.
Old notebook-link preferences stay unused; there is no link-setting interface.

## Multi-collection export in Zotero 10

Use ZPM 1.4.0 with demo collections and a fresh output folder. Restore the previous
default export folder afterward if you change it during testing.

1. Select two sibling subcollections with Command-click (macOS) or Ctrl-click
   (Windows/Linux), right-click a selected row, and run **ZPM → Export → Collection**.
   Expect at most one destination prompt, two workspaces, and one combined result.
2. Repeat with **Collection + Annotations** and verify each workspace's notes.
   Export again unchanged and check that PDFs are skipped in both workspaces.
3. Select a parent and a child, including with the child selected first. Confirm
   the child appears within the parent workspace once, with an explanatory result.
   Select the child alone and verify its parent and siblings are excluded.
4. Try two collections with the same name. Verify separate workspaces, with a
   Zotero-key suffix where needed, and repeat exports updating the correct files.
5. Add a saved search or library row to the selection. Export must be disabled.
   Selecting collections across libraries must also disable Export. Copy Link
   stays disabled for multiple selected collections.
6. Cancel the folder picker once. Confirm nothing exports and another export
   can start. While an export is running, a second command must not overlap it.
7. In the disposable output folder, create an unmanaged folder matching one
   demo collection's name. That collection must fail without overwriting the
   folder; other selected collections must still export. The summary must name
   both the failure and the successful workspaces.

## Optional CLI checks

The installed Homebrew/pipx CLI does not change when the plugin is upgraded.
Use the checkout's environment to test this source version:

```bash
.venv/bin/python -m zotero_project_manager export --help
.venv/bin/python -m zotero_project_manager export "My-AI/Agentic_AI" --output /Users/sbilmis/scratch/zpm_test --annotations --dry-run
```

Use the collection's exact path or key from `zpm list` if its selector differs.
App-specific options (`--to`, `--notebook-url`, `--devonthink-group`,
`--prepare-only`, and `--profile`) are no longer accepted. A named project saved
with `export_profile = "notebooklm"` reports a migration error without exporting.
To deliberately use standard export, review that project's output folder/layout
and remove the `export_profile` setting in its TOML config. Standard projects
from older previews continue to work.

## Reporting a problem

Record the plugin version, selected collection, action, exact error, output path,
and whether the issue occurs in Settings or during export. Redact private document
contents and paths when reporting publicly.

## PDF edits and sync direction

Exports only copy from Zotero to the workspace. Unchanged PDFs are skipped; new
or differing PDFs are copied in full. There is no bidirectional sync or import-back
command. An exported PDF edited in an external reader can be overwritten on the
next export. Keep those edits separately before re-exporting. Zotero reader
annotations and notes are exported as Markdown, not embedded into the copied PDF.

## Links and Emacs picker checks

User instructions live in the [quick start](QUICKSTART.md),
[setup guide](EMACS-SETUP.md), [link reference](LINKS.md), and
[picker reference](PAPER-PICKER.md).

From the repository root, with the development dependencies installed:

```sh
node --check zotero-plugin/links.js
node --test zotero-plugin/tests/*.test.cjs
emacs --batch -Q -l zotero-plugin/tests/org-links.test.el
emacs --batch -Q -l zotero-plugin/tests/org-picker.test.el
.venv/bin/python -m pytest
python3 scripts/build_zotero_plugin.py
```

Node tests simulate Zotero APIs and cover selection, link formatting, reader
hooks, atomic multiple-link copying, endpoint permissions, and cleanup. Emacs
tests exercise real Org activation with process calls mocked, plus picker
requests, insertion, cancellation, UTF-8, and collection-keyword persistence.
The XPI builder verifies the package against the update feed's checksum and
compatibility range. Automated tests do not install the XPI or launch Zotero.

For a manual acceptance check, use demo records and a disposable Org note:

1. Install the plugin and load both Emacs files using the setup guide.
2. Copy and activate a collection, record, collection-specific record, PDF,
   physical PDF page, and saved annotation link. Try Markdown links in your
   target editor as well. For the annotation-menu fix, right-click one saved
   highlight both on the PDF page and in the annotations sidebar. Confirm the
   three **ZPM: Copy Annotation Link (format)** commands appear directly and each
   copies a link to that highlight. Select multiple annotations and confirm all
   three commands are disabled. Plain page text and thumbnails should still use
   **ZPM → Copy PDF Page Link → format**.
3. Copy a mixed record/PDF selection and confirm separate links. Add an unsupported
   note and confirm copying is disabled. Check a group-library entry separately.
4. Select a personal collection, use both picker commands, and cancel once with
   **C-g**. Confirm only directly contained paper records appear.
5. Remember a collection, save and reopen the note, and change Zotero's selected
   collection. Confirm the note still uses the remembered collection; forget it,
   save again, and confirm the picker follows Zotero's selection.
6. Check local-access error help in a disposable test profile where changing the
   permission does not affect an existing workflow. Opening help must not change
   the setting or edit the note.

The picker registers `GET /zpm/papers` on Zotero's local HTTP server. It reads
the selected collection or an explicit `?collection=KEY`, returns collection
identity and paper key/title/authors/year, and respects the local API permission.
It rejects browser-origin requests and unregisters when disabled. The Emacs
client uses loopback with a bounded timeout, no proxy/cookies, and no redirects.
Org handlers validate destinations before passing one URI argument to
`/usr/bin/open`; no shell is involved.

Upstream references:

- [Zotero local API and permission setting](https://www.zotero.org/support/dev/web_api/v3/local_api)
- [Collection/item/PDF URI routing](https://github.com/zotero/zotero/blob/main/chrome/content/zotero/ZoteroProtocolHandler.mjs)
- [Reader context-menu events](https://github.com/zotero/zotero/blob/main/chrome/content/zotero/xpcom/reader.js)
- [PDF-opening preference handling](https://github.com/zotero/zotero/blob/main/chrome/content/zotero/xpcom/fileHandlers.js)
