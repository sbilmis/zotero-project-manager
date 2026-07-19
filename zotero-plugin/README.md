# Zotero Project Manager plugin for Zotero 9

The plugin adds **Export with zpm** to Zotero's collection context menu and performs
the complete export inside Zotero. It requires no Python installation, Homebrew,
pipx, executable path, or subprocess.

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
