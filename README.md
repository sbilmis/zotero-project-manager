# Zotero Project Manager (`zpm`)

`zpm` creates clean, ordinary project folders from Zotero collections. Zotero
remains the source of truth; `zpm` only reads its database and attachments and
writes into a separate output directory.

The current release supports recursive collection export, multiple collections,
portable metadata-based filenames, incremental updates, SHA-256 verification,
safe pruning, dry runs, diagnostics, and a versioned JSON manifest.

## Quick start: export `My-AI`

On this Mac, `zpm` is installed as a user-local command and can be run from any
directory. Export `My-AI` with:

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

## Safety model

- The Zotero database is opened with SQLite `mode=ro` and `PRAGMA query_only`.
- Queries run in a consistent read-only SQLite transaction. Optional
  `--snapshot` mode uses the SQLite backup API when an isolated copy is useful.
- `zpm` never renames, moves, or edits Zotero files.
- Output paths inside the Zotero data directory are rejected.
- Existing directories without a `zpm` manifest are rejected unless explicitly
  adopted with `--overwrite`.

Always keep independent backups of important research data.

## Requirements and installation

- Python 3.11 or newer

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

For a checkout at `~/zotero-collection-mirror`, create its environment once:

```bash
cd ~/zotero-collection-mirror
python -m venv .venv
.venv/bin/pip install -e .
```

Load the convenience functions in the current shell:

```bash
source ~/zotero-collection-mirror/scripts/zpm-helper.sh
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
source ~/zotero-collection-mirror/scripts/zpm-helper.sh
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
--overwrite                        Adopt an unmanaged destination
--verbose                          Enable diagnostic messages
--linked-attachment-base-dir PATH  Resolve Zotero relative linked files
--snapshot                         Query an isolated temporary database copy
```

Collection selectors are matched first by exact Zotero key, then by
case-insensitive full collection name. Ambiguous names produce an error listing
the usable keys.

## Incremental behavior

Each workspace contains `manifest.json` and `README.md`. On later runs, `zpm`
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

Manifest v1 workspaces are read automatically. The next successful export adds
hashes and upgrades the manifest to v2; `status` and `--dry-run` never rewrite it.

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
    models.py       shared domain dataclasses
    diagnostics.py  read-only doctor checks
    utils.py        logging and path safety helpers
```

## Non-goals for v0.2

Better BibTeX, annotations, tags, DOI export, metadata sidecars, DEVONthink or
NotebookLM automation, watch mode, a GUI, and symlink mode are not implemented yet.
