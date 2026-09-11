# Test the simplified exporter with Agentic_AI

This guide targets Zotero plugin **1.1.0**. It exports to one standard workspace
per collection, with no Gemini Notebook or DEVONthink integration. Existing export
folders are not removed by upgrading.

## 1. Install or update the stable release

1. Existing users can run **Tools → Plugins → gear → Check for Updates**.
   For a manual install, download `zpm-zotero-1.1.0.xpi` from the
   [1.1.0 release](https://github.com/sbilmis/zotero-project-manager/releases/tag/v1.1.0).
   To build it from the release source checkout:

   ```bash
   python3 scripts/build_zotero_plugin.py
   ```

2. In Zotero, open **Tools → Plugins → gear → Install Plugin From File…** and
   select the XPI. Install over the existing plugin; no uninstall is needed.
3. Restart Zotero if requested and confirm **Zotero Project Manager 1.1.0** is enabled.
4. Right-click **My-AI → Agentic_AI → Export with zpm**. Expect exactly:

   - **Export Collection**
   - **Export Collection + Annotations**
   - **Settings…**

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
2. Right-click **Agentic_AI → Export with zpm → Export Collection + Annotations**.
3. Expect an **Export complete** summary and the path
   `/Users/sbilmis/scratch/zpm_test/Agentic_AI` if you selected that parent folder.
4. Open that folder in Finder yourself. Check PDFs, generated annotation/child-note
   Markdown, and any selected non-PDF attachments. Their placement follows the
   workspace layout: `Annotations/`, sidecars, or per-paper bundles.
5. No browser, Notebook, DT4, AppleScript prompt, or automatic upload should occur.
   No new `Agentic_AI - NotebookLM` workspace should be created.

Selecting Agentic_AI includes its descendants, not its My-AI parent or siblings.
**Export Collection** uses the same workspace without generating new annotation
documents; previously exported files can remain, since ordinary exports do not prune.

## 4. Check repeat export and existing-folder preservation

1. Re-export Agentic_AI with the same action. Unchanged PDFs should be counted as
   unchanged, with no app-specific duplicate workspace created.
2. If an old `Agentic_AI - NotebookLM` folder already exists, it will still exist.
   The upgrade and standard export do not delete or update it; that is intentional.
3. Restart Zotero and confirm Settings and the simplified menu remain correct.
4. If using the files elsewhere, open that app yourself and select only the files
   you want. Keep hidden `.zpm/` bookkeeping out of imports/uploads. Choose file
   types the destination accepts. zpm does not manage external copies or sources.

No cleanup of old exported folders, Google notebooks, or DT4 records is performed.
Old notebook-link preferences stay unused; there is no link-setting interface.

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
