# Zotero Project Manager plugin for Zotero 9

The plugin adds **Zotero Project Manager → Export** to Zotero's collection context menu and performs
the complete export inside Zotero. It requires no Python installation, Homebrew,
pipx, or executable configuration. Folder exports remain entirely in Zotero;
no external app handoffs, AppleScript, or uploads are performed.

The plugin reads collections, metadata, attachments, notes, and annotations through
Zotero's in-process APIs. It copies files outward to the selected export directory
and never writes to `zotero.sqlite`, Zotero attachments, or Zotero's annotation cache.

## Settings

Open **Settings…** from a collection's **Zotero Project Manager** menu, or open Zotero
**Settings → Zotero Project Manager**, to configure:

- the default output parent folder;
- whether to include non-PDF attachments such as `README.md`, text, images, or data;
- portable attachment filename ordering;
- `separate`, `sidecar`, or `bundle` annotation layout.

The first export prompts for a destination if no valid default exists. Later exports
update the collection's existing workspace without asking again.

Version **1.1.0** includes the settings initialization fix: the saved folder appears on
opening the pane, and **Choose…** opens a native folder-selection dialog attached
to Settings. Cancel preserves the current folder. You can also type an absolute
folder path and leave the field to save it; the status below confirms the change.

## Standard export workflow

The collection menu contains **Zotero Project Manager → Export → Collection**
and **Collection + Annotations**, with **Settings…** beside Export. Both exports use the same standard workspace;
repeat exports update it rather than creating an app-specific copy. Existing
workspaces retain their recorded layout and filename settings.

Use the exported files manually in an app of your choice. The experimental
Gemini Notebook and DEVONthink actions, link setup, and Notebook-specific export
format are not included in the stable release. Existing exported folders, saved preferences,
notebooks, and DT4 records are left untouched. Old notebook links are unused.

See [the Agentic_AI test guide](../docs/TESTING.md) for installation and checks.

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

## Native note links (1.2.0)

**Zotero Project Manager → Copy Link** is a separate collection/item context submenu. It copies
Org, Markdown, and plain URI links without exporting. Paper links select records;
PDF links address the attachment itself. PDF reader context menus also support
physical page and saved annotation links. Dedicated batch commands accept two or
more paper/PDF selections from My Library and reject the entire batch if any
entry is unsupported. Existing export commands and settings are unchanged.

See [the beginner link guide](../docs/LINKS.md) for installation and testing.

For a paper inside a collection, **Zotero Project Manager → Copy Link in This
Collection** offers Org, Markdown, and Zotero URI formats that preserve that
collection context. Ordinary item and PDF links remain unchanged.

## Emacs collection picker preview

Version 1.3.0pre2 adds a read-only local collection/paper endpoint for the Emacs
picker. It respects the local API permission and only exposes personal-library
paper metadata. See [the picker guide](../docs/PAPER-PICKER.md) for the Emacs
module, installation, commands, and manual checks. No new Zotero menus are needed.
