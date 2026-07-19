# Zotero Project Manager (`zpm`)

`zpm` creates clean, ordinary project folders from Zotero collections. Zotero
remains the source of truth; `zpm` only reads its database and attachments and
writes into a separate output directory.

The current release supports recursive collection export, multiple collections,
configurable portable filenames, incremental updates, SHA-256 verification,
safe pruning, DOI/tag metadata, opt-in annotation and child-note Markdown with
three workspace layouts, research indexes, comprehensive diagnostics, a self-contained
Zotero 9 plugin with a settings pane, and a versioned JSON manifest.

## Quick start: export `My-AI`

After installation, `zpm` can be run from any directory. Export `My-AI` with:

```bash
zpm export "My-AI" --output ~/ResearchProjects
```

The files are written to:

```text
~/ResearchProjects/My-AI/
```

Preview the export without writing anything:

```bash
zpm export "My-AI" --output ~/ResearchProjects --dry-run --verbose
```

Run the same `zpm export` command whenever the Zotero collection changes. The
manifest makes the update incremental: new or changed PDFs are copied and
unchanged PDFs are left alone.

Include PDF annotations and Zotero child notes as Markdown:

```bash
zpm export "My-AI" --output ~/ResearchProjects --annotations
```

Inspect changes without writing anything:

```bash
zpm status "My-AI" --output ~/ResearchProjects
```

Preview files removed from Zotero that can be safely pruned:

```bash
zpm status "My-AI" --output ~/ResearchProjects --prune
```

After reviewing the preview, apply safe pruning:

```bash
zpm export "My-AI" --output ~/ResearchProjects --prune
```

Only manifest-owned files whose SHA-256 still matches are deleted. Files changed
outside `zpm`, files without a trusted hash, and unsafe paths are protected.

Other useful global commands:

```bash
zpm list
zpm doctor --output ~/ResearchProjects
zpm export --help
zpm --version
```

## Zotero 9 companion plugin

The self-contained companion plugin adds **Export with zpm** to a collection's
right-click menu in Zotero 9. It does not require Python, Homebrew, pipx, or an
external executable:

```text
Export with zpm
    Export Collection
    Export Collection + Annotations
    Settings…
```

Download the versioned `.xpi` from the matching GitHub release.
In Zotero, open **Tools → Plugins**, use the gear menu, choose
**Install Plugin From File…**, and select the downloaded XPI.

Open **Settings…** from the collection menu, or open Zotero **Settings → Zotero
Project Manager**, to choose the output folder, include non-PDF attachments such as
`README.md`, select filename ordering, and choose the annotation layout. The plugin
reads the selected collection through Zotero's in-process APIs and performs copying,
hashing, manifests, metadata, and annotation rendering itself. It never reads or
writes `zotero.sqlite` directly.

Zotero installs compatible plugin releases automatically when **Tools → Plugins →
gear → Update Add-ons Automatically** is enabled. **Check for Updates** in the same
menu remains available as a manual fallback. The versioned update feed uses immutable,
SHA-256-verified XPI release assets.

The Python `zpm` CLI remains available separately for terminal workflows, scheduled
exports, CI, safe pruning, and full verification. The Zotero plugin does not depend on it.

### Plugin and CLI responsibilities

The plugin and CLI share the same core workspace format and export behavior, but the
CLI intentionally retains advanced administration and automation features:

| Capability | Zotero plugin | Python CLI |
| --- | --- | --- |
| PDFs, optional non-PDF files, metadata, annotations, notes, and images | Yes | Yes |
| Recursive collections, filename templates, layouts, and incremental SHA-256 updates | Yes | Yes |
| Multiple root collections in one operation | One at a time | Yes |
| Dry-run, status, pruning, full verification, and unmanaged-folder adoption | No | Yes |
| Diagnostics, named projects, saved TOML configuration, and scheduled automation | No | Yes |
| Linked-attachment base-directory and SQLite snapshot controls | No | Yes |
| Runs without Python or direct SQLite access | Yes | No |

This keeps the interactive plugin focused and conservative while the CLI provides
batch operations and explicit file-deletion or workspace-adoption controls.

## Doctor and readiness checks

Run a human-readable readiness audit:

```bash
zpm doctor --output ~/ResearchProjects
```

It reports the zpm/Python runtime, Zotero application version and running state,
data and database locations, read-only SQLite access, collection count, available,
missing, or unresolved attachments, configuration location, storage, and output
safety. Machine-readable output is available for support tooling:

```bash
zpm doctor --output ~/ResearchProjects --json
```

Errors produce a nonzero exit status. Warnings identify optional or transient
conditions without changing Zotero or the workspace.

## Configuration and named projects

Set global defaults once:

```bash
zpm config set --zotero-dir ~/Zotero --output ~/ResearchProjects
zpm config show
```

The default configuration file is `~/.config/zpm/config.toml`. Override it with
the global `--config PATH` option or the `ZPM_CONFIG` environment variable.

Create a named project from one or more collections:

```bash
zpm project add ai "My-AI" "Claude"
zpm project list
zpm project show ai
```

Synchronize it from any directory:

```bash
zpm sync ai
zpm sync ai --dry-run
```

A named project can save recursive traversal, non-PDF inclusion, pruning, full
hash verification, metadata and annotation generation, filename ordering, and its
own output directory. Use `--force` with `zpm project add` to replace an existing
project definition.

For example:

```bash
zpm project add ai "My-AI" --annotations --filename-template year_author_title --force
zpm sync ai
```

## Metadata and research index

Exports generate two control files under the workspace's hidden `.zpm/` directory by default:

- `.zpm/metadata.json` contains collection keys, Zotero item and attachment keys,
  titles, dates, creators, DOI, tags, source and destination paths, state, and SHA-256.
- `.zpm/INDEX.md` provides a human-readable table with DOI links and relative file links.

Disable these generated artifacts when needed:

```bash
zpm export "My-AI" --output ~/ResearchProjects --no-metadata
```

For safety, `zpm` refuses to overwrite an existing `.zpm/metadata.json` or `.zpm/INDEX.md`
unless that file was previously generated by `zpm`.

## Annotations and child notes

Annotation export is opt-in because comments and notes may contain private research
material:

```bash
zpm export "My-AI" --annotations
```

It includes highlights, underlines, comments, colors, page labels, annotation tags,
modification dates, image/ink annotations, and child notes. Cached image and ink
annotation previews are copied as PNG files into a managed `.assets` folder beside
the Markdown document and embedded with relative Markdown links. If Zotero has no
cached preview, the Markdown records that fact instead of failing the whole export.
For items in the personal Zotero library, links open the PDF or annotation in Zotero.

Generated annotation files and asset folders carry safety markers. `zpm` refuses to
replace unmanaged Markdown or manage an existing unmarked asset folder, and avoids
rewriting unchanged generated files. Zotero, its database, PDFs, and annotation cache
remain read-only.

### Annotation layouts

Choose the layout that matches how the exported workspace will be used:

- `separate` (default) keeps the PDF hierarchy clean and puts generated material
  under a parallel `Annotations/` hierarchy.
- `sidecar` puts `paper.annotations.md` and `paper.annotations.assets/` beside
  `paper.pdf`; this is convenient for normal file browsing.
- `bundle` creates one folder per paper containing the PDF, `annotations.md`, and
  `annotations.assets/`; this is convenient when a paper should move as one unit.

```text
separate/                         sidecar/
  Books/paper.pdf                   Books/paper.pdf
  Annotations/Books/paper.md        Books/paper.annotations.md

bundle/
  Books/paper/
    paper.pdf
    annotations.md
    annotations.assets/
```

Select a layout for one export:

```bash
zpm export "My-AI" --annotations --annotation-layout sidecar
```

Save a global default or a named-project preference:

```bash
zpm config set --annotation-layout bundle
zpm project add ai "My-AI" --annotations --annotation-layout bundle --force
```

The selected layout is recorded in manifest v4. An existing workspace cannot be
silently reorganized by changing this setting; choose a new output parent when
switching layouts.

## Filename preferences

The default remains `author_year_title`, producing names such as:

```text
Curie - 2024 - Paper title.pdf
```

Choose another preset for a direct export:

```bash
zpm export "My-AI" --filename-template year_author_title
```

Available presets are:

- `author_year_title`
- `author_title_year`
- `year_author_title`
- `year_title_author`
- `title_author_year`
- `title_year_author`
- `author_title`
- `year_title`
- `title_author`
- `title_year`
- `title`

The six three-part presets cover every possible ordering of author, year, and title.
The shorter presets always retain the title while allowing the author or year to be
omitted. Missing Zotero metadata is skipped gracefully in every preset.

Set a global default:

```bash
zpm config set --filename-template year_author_title
```

Or save it in a named project:

```bash
zpm project add ai "My-AI" --filename-template year_author_title --force
```

The selected template is recorded in the workspace manifest. To avoid unsafe or
surprising renames, changing the template for an existing workspace is rejected;
export to a new output directory when reorganizing existing filenames.

## Safety model

- The Zotero database is opened with SQLite `mode=ro` and `PRAGMA query_only`.
- Queries run in a consistent read-only SQLite transaction. Optional
  `--snapshot` mode uses the SQLite backup API with a hard timeout when an
  isolated copy is useful.
- Companion-plugin exports use Zotero 9's in-process read APIs and never open
  `zotero.sqlite`.
- `zpm` never renames, moves, or edits Zotero files.
- Output paths inside the Zotero data directory are rejected.
- Existing directories without a `zpm` manifest are rejected unless explicitly
  adopted with `--overwrite`.

Always keep independent backups of important research data.

## Requirements and installation

- macOS with Homebrew, or Python 3.11 or newer

The recommended macOS installation is Homebrew:

```bash
brew install sbilmis/tap/zpm
```

Upgrade a Homebrew installation with:

```bash
brew update
brew upgrade zpm
```

Alternatively, install the published Python package globally with `pipx`:

```bash
brew install pipx
pipx install zotero-project-manager
```

Upgrade an existing `pipx` installation with:

```bash
pipx upgrade zotero-project-manager
```

Install from a checkout:

```bash
python -m pip install .
```

For development:

```bash
python -m pip install -e '.[dev]'
pytest
```

## Usage

### Optional shell helpers

For a checkout at `~/developer/projects/zotero-project-manager`, create its environment once:

```bash
cd ~/developer/projects/zotero-project-manager
python -m venv .venv
.venv/bin/pip install -e .
```

Load the convenience functions in the current shell:

```bash
source ~/developer/projects/zotero-project-manager/scripts/zpm-helper.sh
```

Then use:

```bash
zpm_collections
zpm_my_ai
zpm_export "My-AI" "Claude"
zpm_export "My-AI" --dry-run --verbose
```

The helpers default to `~/Zotero` and `~/ResearchProjects`. Override these
locations before sourcing the file when needed:

```bash
export ZPM_ZOTERO_DIR="/path/to/Zotero"
export ZPM_OUTPUT_DIR="/path/to/ResearchProjects"
source ~/developer/projects/zotero-project-manager/scripts/zpm-helper.sh
```

List collections, including the keys needed to disambiguate duplicate names:

```bash
zpm list
zpm list --zotero-dir ~/Zotero
```

Export one collection to the current directory:

```bash
zpm export "My-AI"
```

Export several collections beneath a chosen parent directory:

```bash
zpm export "My-AI" "Claude" "Image_Processing" --output ~/ResearchProjects
```

Useful options:

```text
--recursive / --no-recursive       Include descendants (default: recursive)
--pdf-only / --include-non-pdf     Attachment filter (default: PDF only)
--dry-run                          Show counts without writing
--prune                            Safely remove hash-verified stale exports
--verify                           Fully recompute source and destination hashes
--metadata / --no-metadata        Enable or disable metadata and index generation
--annotations / --no-annotations  Export annotations and child notes as Markdown
--annotation-layout LAYOUT        separate, sidecar, or bundle
--filename-template PRESET        Select metadata component ordering
--overwrite                        Adopt an unmanaged destination
--verbose                          Enable diagnostic messages
--linked-attachment-base-dir PATH  Resolve Zotero relative linked files
--snapshot                         Query an isolated temporary database copy
```

Collection selectors are matched first by exact Zotero key, then by
case-insensitive full collection name. Ambiguous names produce an error listing
the usable keys.

## Incremental behavior

Each workspace contains `.zpm/manifest.json` and `.zpm/export-summary.md`. Keeping
generated control data under `.zpm/` leaves names such as `README.md`, `INDEX.md`, and
`metadata.json` available for ordinary Zotero attachments. On later runs, `zpm`
uses recorded source and destination metadata plus SHA-256 digests to:

- leave unchanged files alone;
- replace changed managed files;
- copy newly discovered files;
- report missing source attachments without deleting an earlier export.
- reconcile identical files re-added under a new Zotero attachment key;
- track files removed from the collection until they are safely pruned.

`--overwrite` is not needed for normal updates. It is the explicit opt-in for
adopting an existing directory or replacing an unmanaged filename conflict.
Use `--verify` for a full content audit even when file metadata appears unchanged.

Root-level manifest v1–v4 workspaces are read and migrated automatically. A successful
export writes manifest v4 under `.zpm/`; `status` and `--dry-run` never rewrite it.

## Troubleshooting

### Zotero database is locked

Zotero can normally remain open because `zpm` uses read-only SQLite access and
waits briefly for transient locks. An export may still be blocked while Zotero
is syncing, upgrading its database, or performing maintenance.

If `zpm` reports that the database is locked:

1. Wait for Zotero synchronization or maintenance to finish, then retry.
2. If it remains locked, close Zotero completely and run the command again.
3. Use `zpm doctor --output ~/ResearchProjects` to check the configuration.
4. When Zotero must remain open, use the Zotero 9 companion plugin; its in-process
   API does not open the SQLite database directly.

`zpm` does not modify Zotero when a lock occurs. A lock error happens before the
collection can be read or any export changes are applied.

## Attachment paths

Stored Zotero attachments (`storage:...`), absolute linked paths, and `file://`
paths are resolved automatically. Zotero's `attachments:...` relative paths
require `--linked-attachment-base-dir` because that preference is not stored in
`zotero.sqlite`.

## Development layout

```text
src/zotero_project_manager/
    cli.py          CLI parsing and presentation
    zotero.py       read-only SQLite and attachment path resolution
    collections.py hierarchy, lookup, and traversal
    exporter.py     safe incremental export orchestration
    filenames.py    portable filename generation and collisions
    manifest.py     versioned manifest serialization
    metadata.py     JSON metadata and Markdown research indexes
    annotations.py  annotation and child-note Markdown generation
    bridge.py       validated lock-free Zotero plugin snapshots
    source.py       read-only exporter source interface
    models.py       shared domain dataclasses
    diagnostics.py  read-only doctor checks
    config.py       TOML defaults and named projects
    utils.py        logging and path safety helpers

zotero-plugin/
    bootstrap.js    Zotero 9 lifecycle hooks
    native-exporter.js incremental JavaScript export engine
    zpm.js          context menu, Zotero data capture, and filesystem adapter
    preferences.*   Zotero settings pane for paths, attachments, names, and layout
    manifest.json   Zotero compatibility and update metadata
```

## Current non-goals and roadmap

Better BibTeX export, DEVONthink or automatic personal NotebookLM uploads, watch
mode, a standalone GUI, and symlink mode are not implemented. They
remain possible future additions; Zotero continues to be the source of truth.
