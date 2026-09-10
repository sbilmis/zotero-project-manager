# Test remembered Notebook links with Agentic_AI

This guide targets Zotero plugin **1.1.0pre3**. The feature remembers a notebook
link; it does not create/name notebooks, log into Google, or upload automatically.
The Python CLI still uses its explicit `--notebook-url` argument.

## 1. Install the preview

1. Use the locally built `dist/zpm-zotero-1.1.0pre3.xpi`. If you downloaded the
   source checkout instead, build it from the repository root with:

   ```bash
   python3 scripts/build_zotero_plugin.py --development
   ```

2. In Zotero, open **Tools → Plugins → gear → Install Plugin From File…**, select
   the XPI, and restart Zotero if requested.
3. Confirm **Zotero Project Manager 1.1.0pre3** is listed and enabled.
4. Right-click **My-AI → Agentic_AI**, then choose **Export with zpm → Settings…**.
   Set a permanent output parent folder such as a ResearchProjects folder in your
   Documents. Do not use Zotero's storage folder or a temporary directory.
5. Check that a few PDFs in this collection open locally. Enable **Include other
   attached files** if you also want non-PDF attachments delivered to DT4.

Only Agentic_AI and its descendants are exported when you select Agentic_AI.
Selecting My-AI instead exports that parent and all its descendants.

## 2. Save the notebook once

1. In your usual browser, sign into the intended Google account and open/create
   the notebook **Agentic_AI**. Copy its full address from the address bar.
2. In Zotero, right-click **Agentic_AI → Export with zpm → Set Gemini Notebook
   Link…**.
3. Paste the notebook URL and click **OK**. Expect **Link saved for Agentic_AI**.
   Saving the link should not export files or open apps.

The URL must point to an actual notebook under notebook.google.com or
notebooklm.google.com, not the site's home page or a generic Gemini chat.
Account selectors present in the URL are kept, but browser account selection
still matters. If Google says access denied, use the correct account or replace
the link; the plugin does not create a replacement notebook.

## 3. Test the send

1. Right-click **Agentic_AI → Export with zpm → Send to Gemini Notebook…**.
2. After export, dismiss **Ready for Gemini Notebook**. There should be no
   notebook-link prompt now.
3. Confirm the browser opens your saved notebook directly, not the home page.
4. Finder should select the current prepared source files in the separate
   **Agentic_AI - NotebookLM** workspace. If macOS requests permission, allow
   Zotero to control Finder.
5. In the notebook, choose **Add sources** and drag the selected files into the
   upload area, or choose **Upload files**. Include the annotation Markdown files
   and collection overview as desired; exclude the hidden `.zpm` directory.
6. Wait for processing and check the notebook's Sources panel yourself.

This is a real Google upload if you perform step 5. For a routing-only test,
stop at step 4; nothing will have been uploaded by zpm.

## 4. Test persistence and editing without uploading again

1. Quit and reopen Zotero. Send Agentic_AI again.
   **Expected:** the same notebook opens with no link prompt. Do not re-upload
   the files just to test persistence; repeat uploads can duplicate sources.
2. Open **Set Gemini Notebook Link…** again.
   **Expected:** the current link is prefilled. Click **Cancel**.
3. Optional: paste another notebook URL you own and click OK, then Send again.
   **Expected:** only Agentic_AI's destination changes. Restore its original URL
   afterward.
4. Try the Notebook home-page URL in the link dialog.
   **Expected:** a validation error, with the previous saved link unchanged.
   Click Cancel to leave it as it was.
5. To test forgetting: open the dialog, empty the field, and click OK.
   **Expected:** the link is cleared, but no notebook or sources are deleted.
   On the next Send, the setup prompt returns. Paste the original link to save
   it again.

On an unlinked collection, blank input in the first-send prompt opens the Notebook
home page without remembering it. Cancel stops the handoff; already exported
files remain. Links are local to this Zotero profile, not synced between Macs.
They are keyed by library and collection identity, not the collection's title.

## 5. Check DT4 remains independent

1. Open **DEVONthink 4** and a writable test database.
2. Right-click Agentic_AI in Zotero → **Export with zpm → Send to DEVONthink 4…**.
3. Select your test group. Approve macOS automation permission if requested.
4. Confirm the Agentic_AI group contains links to files under the permanent export
   folder. The saved Google notebook URL is irrelevant to this action.
5. Send again to the same database and confirm existing indexed paths are reused.

DT3 must never be targeted. Keep the export folder: DT4 indexes those copies.
Zotero originals are not modified, and zpm does not prune existing DT4 records.

## Reporting a problem

Record the plugin version, collection name, action, exact error, and whether the
browser, Finder, or DT4 opened. If a notebook/source is private, redact its URL
and document contents from public issues. Note separately whether the export
completed and whether the app handoff succeeded.
