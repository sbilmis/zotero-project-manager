# zpm companion plugin for Zotero 9

This optional plugin adds **Export with zpm** to Zotero's collection context
menu. It reads collection data through Zotero's in-process APIs and passes a
temporary JSON snapshot to the installed `zpm` executable. It never writes to
`zotero.sqlite` and removes the temporary snapshot after each command.
For image and ink annotations, it passes only the path of an existing Zotero cache
PNG; the Python exporter copies that file outward and never changes Zotero's cache.

The plugin requires Zotero 9 and an installed `zpm` command. On macOS, the
Homebrew installation is detected automatically at `/opt/homebrew/bin/zpm` or
`/usr/local/bin/zpm`. Use **Choose zpm Executable…** in the collection menu for
pipx, virtual-environment, or other custom installations.

Open **Settings…** from the collection menu, or open Zotero **Settings → Zotero
Project Manager**, to configure:

- the default output parent folder;
- a custom zpm executable and installation test;
- `separate`, `sidecar`, or `bundle` annotation layout.

The layout is passed to the Python exporter and recorded in the workspace manifest.
To protect existing exports from unexpected rearrangement, use a new output parent
when changing a workspace's layout.

Install the `.xpi` asset from the matching zpm GitHub release through
**Zotero → Tools → Plugins → gear menu → Install Plugin From File…**.

To update an installed copy, open **Tools → Plugins**, use the gear menu, and choose
**Check for Updates**. The plugin's manifest points Zotero to the repository's
versioned update feed, which contains SHA-256-verified GitHub release assets.
