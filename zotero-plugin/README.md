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

Install the `.xpi` asset from the matching zpm GitHub release through
**Zotero → Tools → Plugins → gear menu → Install Plugin From File…**.
