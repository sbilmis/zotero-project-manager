# Zotero Project Manager (ZPM)

ZPM exports Zotero collections into clean, ordinary research
folders. Zotero remains the source of truth: the project reads Zotero data and copies
attachments outward without modifying the library, database, or original files.

Use the self-contained Zotero 9/10 plugin for native note links and interactive exports, or the Python CLI for
batch operations, automation, verification, and safe pruning.

**Start here:** [Plugin quick start](docs/PLUGIN-QUICKSTART.md)
· [Markdown and Org links](docs/QUICKSTART.md)
· [Download ZPM](https://github.com/sbilmis/zotero-project-manager/releases/latest)

## Choose an interface

| Capability | Zotero plugin | Python CLI |
| --- | --- | --- |
| PDFs and optional non-PDF attachments | Yes | Yes |
| Metadata, annotations, notes, and cached annotation images | Yes | Yes |
| Recursive hierarchy, filename presets, and three annotation layouts | Yes | Yes |
| Incremental SHA-256 synchronization and legacy workspace migration | Yes | Yes |
| Multiple root collections in one operation | Zotero 10 with ZPM 1.4.0+ | Yes |
| Dry-run, status, pruning, full verification, and workspace adoption | No | Yes |
| Diagnostics, named projects, saved configuration, and automation | No | Yes |
| Runs without Python or direct SQLite access | Yes | No |

Both interfaces produce the same managed workspace format. The plugin stays focused
and conservative; the CLI provides explicit administrative controls.

## Zotero plugin

Follow the [plugin quick start](docs/PLUGIN-QUICKSTART.md) for installation,
your first export, repeat exports, link copying, and settings.

Zotero 10.0.x requires ZPM **1.3.2** or newer. ZPM 1.3.2 also supports Zotero 9.
Multi-collection export is available in **ZPM 1.4.0** with Zotero 10.
ZPM 1.3.2 exports one selected collection at a time. Copying a collection
link and the Emacs picker still require a single collection.
ZPM **1.4.1** fixes annotation-link menus and successful-export dialogs.
See the [1.4.1 release notes](docs/releases/1.4.1.md) for changes,
compatibility, and upgrade instructions.

Exports run inside Zotero and do not require Python, Homebrew, pipx, or an
executable path. Exports create and update local workspaces without launching
other apps, running AppleScript, or uploading files.

Download the XPI from the [latest GitHub release](https://github.com/sbilmis/zotero-project-manager/releases/latest),
then open **Zotero → Tools → Plugins → gear menu → Install Plugin From File…**.
Existing installations can be upgraded in place.

Menu names below use **ZPM** starting with **1.3.1**. Versions through
**1.3.0** display **Zotero Project Manager** instead.

Right-click a collection to use:

```text
ZPM
    Copy Link → Org / Markdown / Zotero URI
    Export → Collection / Collection + Annotations
    Settings…
```

You can export any subcollection directly: its workspace contains that
subcollection and its descendants, without its parent or siblings. In Zotero 10,
ZPM 1.4.0 also exports several selected collections to separate workspaces under
one destination. If a parent and a child are both selected, the child is included
under the parent once. See the [plugin quick start](docs/PLUGIN-QUICKSTART.md#2-export-your-first-collection).

Settings control:

- the default export folder;
- whether non-PDF attachments such as `README.md`, text, images, and data are included;
- attachment filename ordering;
- `separate`, `sidecar`, or `bundle` annotation layout.

The first export asks for a destination if no valid default exists. Zotero can install
future releases automatically when **Update Add-ons Automatically** is enabled in the
Plugins gear menu; **Check for Updates** provides a manual check.

## Native links

Right-click a collection, paper record, or PDF attachment and choose **ZPM → Copy Link**. Copy Org links for Emacs, Markdown links for Obsidian, or plain Zotero
URIs. The PDF reader also offers page and annotation links. Explicit **Copy Multiple Links** commands copy selected paper records and PDFs, one per line. Only My
Library is supported; unsupported entries disable copying and batches never skip
invalid entries. These commands use Zotero’s native clipboard and need neither
Actions & Tags nor zotxt, bibliography styles, or an export folder.

Start with the [quick start](docs/QUICKSTART.md), or see the
[link reference](docs/LINKS.md) for PDF pages, annotations, and multiple links.

## Emacs collection picker

From an Org note, run `M-x zpm-insert-paper-link` or `M-x zpm-open-paper` to browse
papers in the selected Zotero collection by author, year, and title. Remember a
collection per note with `zpm-remember-collection`. Follow the
[one-time setup](docs/EMACS-SETUP.md) to load the Emacs files and enable Zotero's
local API permission. See the [quick start](docs/QUICKSTART.md) for the everyday
workflow and the [picker reference](docs/PAPER-PICKER.md) for collection behavior.

## One workspace, your choice of app

Export a collection once and use its standard folder wherever you need it. For
example, selecting **My-AI → Agentic_AI** exports to **Agentic_AI/** and preserves
its descendants inside that workspace. Re-exporting updates the same workspace.
Choose **Export Collection + Annotations** to include annotations and child notes.

Open the target app yourself and select the exported files you want to use. zpm
has no app-specific Send commands, stored notebook-link UI, automatic app indexing,
uploading, or separate Notebook export format. The hidden `.zpm/` directory is
bookkeeping, not material to upload or import. You choose the files and compatible
types in the destination app.

Stable **1.1.0** keeps the public 1.0.0 feature set and fixes Settings/Choose while
adding concurrent-export protection. The experimental Gemini Notebook/DT4 preview
integrations are not included; standard exports and naming/layout settings remain.
Existing export folders (including old ` - NotebookLM` folders), Google notebooks,
DT4 records, and Zotero originals are not deleted or migrated. Old notebook-link
preferences are left unused; the simplified plugin does not read or clear them.
The earlier implementation remains in Git history.

The CLI no longer accepts `--to`, `--notebook-url`, `--devonthink-group`,
`--prepare-only`, or `--profile`. Existing standard named projects still work.
A saved project with `export_profile = "notebooklm"` is rejected with a migration
message: review its output directory and layout, then remove that setting in its
TOML config only if you want standard export. zpm never silently switches the project
or rewrites the config on load.

See [the Agentic_AI testing guide](docs/TESTING.md) for installation and checks.

## Python CLI

The CLI requires Python 3.11 or newer. Install it on macOS with Homebrew:

```bash
brew install sbilmis/tap/zpm
```

Or install the PyPI package with pipx:

```bash
brew install pipx
pipx install zotero-project-manager
```

Upgrade with `brew upgrade zpm` or `pipx upgrade zotero-project-manager`.

### Quick start

List collections and export one recursively:

```bash
zpm list
zpm export "My-AI" --output ~/ResearchProjects
```

Include annotations and child notes:

```bash
zpm export "My-AI" --output ~/ResearchProjects --annotations
```

Preview changes, then safely prune files removed from Zotero:

```bash
zpm status "My-AI" --output ~/ResearchProjects --prune
zpm export "My-AI" --output ~/ResearchProjects --prune
```

Only manifest-owned files whose SHA-256 still matches are deleted.

### Reusable projects and diagnostics

Save defaults or a named multi-collection project:

```bash
zpm config set --zotero-dir ~/Zotero --output ~/ResearchProjects
zpm project add ai "My-AI" "Claude" --annotations
zpm sync ai
```

Run a read-only readiness audit:

```bash
zpm doctor --output ~/ResearchProjects
```

Use `zpm --help` and `zpm export --help` for every command and option.

## Workspace format

A typical export with **Collection + Annotations** and the **Separate** layout
looks like this:

```text
My-AI/
    Curie - 2024 - Paper title.pdf
    Books/
        Author - 2023 - Book.pdf
    Annotations/
        Curie - 2024 - Paper title.md
    .zpm/
        manifest.json
        metadata.json
        INDEX.md
        export-summary.md
```

Generated control data lives under `.zpm/`, leaving ordinary project names such as
`README.md`, `INDEX.md`, and `metadata.json` available for Zotero attachments.
ZPM generates **`.zpm/export-summary.md`**, not a root `README.md`. A root
`README.md` appears only if you add one yourself or export a matching Zotero
attachment with **Include non-PDF attachments** enabled. The `.zpm` folder is
hidden by default in some file managers (in macOS Finder, press **Command-Shift-.**).

The manifest supports incremental exports:

- unchanged files are left alone;
- new and changed attachments are copied;
- missing or removed attachments are recorded without silently deleting prior copies;
- identical files re-added under a new Zotero key are reconciled;
- root-level manifest v1–v4 workspaces migrate under `.zpm/` after a successful export.

### Does this sync both ways?

No. Export and `zpm sync` run **from Zotero to the workspace only**. The selected
collection and its descendants are scanned on each export; matching attachments
are left alone and only new or differing attachments are copied in full. This is
file-level incremental copying, not rsync block transfers. The plugin compares
SHA-256 hashes; the CLI can reuse hashes when size and modification time match
the manifest (`--verify` forces content verification).

**Re-export can overwrite edits made to an exported PDF**, including highlights
and comments saved by an external reader, even when the Zotero original has not
changed. There is no import-back command, annotation merge, or bidirectional conflict
resolution. Keep such edits in a separate working copy until you deliberately
bring them into Zotero. A changed Zotero PDF replaces its exported copy on the next
export; unchanged PDFs are not recopied. Removed entries stay unless explicitly
pruned with the CLI's hash-checked pruning option.

Zotero reader annotations and child notes are exported as Markdown with
**Collection + Annotations**; ZPM does not embed those annotations into the copied
PDF. Workspace metadata and summaries are refreshed during export.

## Annotations and layouts

Annotation export includes highlights, comments, page labels, tags, child notes, and
available cached image or ink previews. It is opt-in because research notes may contain
private material.

Choose one of three layouts:

- `separate` keeps generated Markdown under a parallel `Annotations/` hierarchy;
- `sidecar` places `paper.annotations.md` beside each PDF;
- `bundle` creates one folder per paper containing the attachment and annotations.

The selected filename preset and layout are recorded in the manifest. Existing
workspaces retain those settings to prevent surprising reorganizations.

## Safety model

- Zotero files, attachments, and annotation caches are never modified.
- The CLI opens `zotero.sqlite` read-only with SQLite query-only protection.
- The plugin reads through Zotero's in-process APIs and does not open SQLite directly.
- Output paths inside the Zotero data directory are rejected.
- Unmanaged workspaces and conflicting user files are not adopted silently.
- Generated annotation and control files carry ownership markers.
- Full verification and pruning require explicit CLI options.

Keep independent backups of important research data.

## Development

```bash
git clone https://github.com/sbilmis/zotero-project-manager.git
cd zotero-project-manager
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/python -m pytest
node --test zotero-plugin/tests/*.test.cjs
```

Build the release XPI and verify its update-feed entry with:

```bash
.venv/bin/python scripts/build_zotero_plugin.py
```

Install `dist/zpm-zotero-1.2.0.xpi` using Zotero's **Tools → Plugins → gear →
Install Plugin From File…**, or use the XPI from the matching GitHub release.
The installed Homebrew/pipx release does not change when this checkout changes;
use `.venv/bin/python -m zotero_project_manager` to run the CLI from this checkout.
For unpublished development versions only, pass `--development` to build without
a published feed entry. Release builds and CI verify the exact update-feed hash.

See [CONTRIBUTING.md](CONTRIBUTING.md), [PUBLISHING.md](PUBLISHING.md), the
[plugin guide](zotero-plugin/README.md), and [CHANGELOG.md](CHANGELOG.md) for focused
development and release details.

ZPM is released under the [MIT License](LICENSE).

For a paper inside a collection, **ZPM → Copy Link in This
Collection** offers Org, Markdown, and Zotero URI formats that preserve that
collection context. Ordinary item and PDF links remain unchanged.
