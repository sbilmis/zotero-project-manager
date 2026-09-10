# Zotero Project Manager plugin for Zotero 9

The plugin adds **Export with zpm** to Zotero's collection context menu and performs
the complete export inside Zotero. It requires no Python installation, Homebrew,
pipx, or executable configuration. macOS app handoffs use the built-in AppleScript
runtime; ordinary folder exports remain entirely in Zotero.

The plugin reads collections, metadata, attachments, notes, and annotations through
Zotero's in-process APIs. It copies files outward to the selected export directory
and never writes to `zotero.sqlite`, Zotero attachments, or Zotero's annotation cache.

## Settings

Open **Settings…** from a collection's **Export with zpm** menu, or open Zotero
**Settings → Zotero Project Manager**, to configure:

- the default output parent folder;
- whether to include non-PDF attachments such as `README.md`, text, images, or data;
- portable attachment filename ordering;
- `separate`, `sidecar`, or `bundle` annotation layout.

The first export prompts for a destination if no valid default exists. Later exports
update the collection's existing workspace without asking again.

## App destinations

Choose **Send to Gemini Notebook…** from a collection's zpm menu to
create a separate `Collection - NotebookLM/` workspace. The plugin flattens supported
attachments, generates sidecar Markdown for PDF annotations and notes, and writes a
`collection-overview.md` guide. Unsupported data files and `.zpm/` control artifacts
are excluded from the prepared source count.

The action opens this collection's saved notebook and selects the prepared sources
in Finder on macOS (other systems reveal the folder). On first use, paste a notebook
URL to remember it or leave the prompt blank to open the home page. Open/create a
notebook if needed and drag the files
into **Add sources**, or use **Upload files**. This final step is manual and uses
your existing Google login. No Chrome extension or Google Drive setup is required.
Check the Sources panel after uploading; repeat uploads can create duplicates.

Choose **Set Gemini Notebook Link…** to save/change a collection's destination
without exporting. Copy the full URL from an open notebook, paste it, and press
OK. Submit an empty value to forget the link; Cancel preserves it. No Google
notebook or source is deleted when a link is forgotten.

Links live in local Zotero preferences, identified by library ID and collection
key. They survive restarts and collection renames, but are not synced across
computers. Google account selectors in the URL are preserved; the plugin does not
inspect login sessions or verify access. Use the account that owns the notebook.
This feature does not automatically create notebooks or upload files.

See [the Agentic_AI test guide](../docs/TESTING.md) for a complete walkthrough.

Choose **Send to DEVONthink 4…** on macOS to export with annotations and link the
current files into a database/group chosen in DT4. DT3 is never selected, even when
both apps are installed: the handoff uses DT4's bundle ID and checks its version.
The collection hierarchy
is retained. Repeated sends refresh already indexed paths and add new files.
Existing DEVONthink records keep their location, and nothing is pruned there.

DEVONthink indexing requires a permanent export folder. Keep that folder in place:
the app is linking to those exported copies. Zotero originals are never indexed or
modified. If macOS asks, allow Zotero to control DEVONthink under
**System Settings → Privacy & Security → Automation**. Finder may request the same
permission when selecting Notebook sources.

Generated manifests, metadata, indexes, and summaries live under `.zpm/`, leaving
normal workspace names available for files attached in Zotero. Existing root-level
manifest v1–v4 workspaces migrate automatically after a successful export.

## Installation and updates

Install the versioned `.xpi` from the matching GitHub release through **Zotero →
Tools → Plugins → gear menu → Install Plugin From File…**.

Zotero installs compatible plugin updates automatically when **Update Add-ons
Automatically** is enabled in the Plugins gear menu. Use **Check for Updates** there
for an immediate manual check. The update feed pins every release to an immutable
GitHub asset and verifies its SHA-256 digest.

The Python `zpm` CLI remains an optional, independent interface for terminal
automation, scheduled exports, safe pruning, and full verification.
