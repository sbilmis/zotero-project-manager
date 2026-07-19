# Zotero Project Manager (`zpm`)

Zotero Project Manager exports Zotero collections into clean, ordinary research
folders. Zotero remains the source of truth: the project reads Zotero data and copies
attachments outward without modifying the library, database, or original files.

Use the self-contained Zotero 9 plugin for interactive exports, or the Python CLI for
batch operations, automation, verification, and safe pruning.

## Choose an interface

| Capability | Zotero plugin | Python CLI |
| --- | --- | --- |
| PDFs and optional non-PDF attachments | Yes | Yes |
| Metadata, annotations, notes, and cached annotation images | Yes | Yes |
| Recursive hierarchy, filename presets, and three annotation layouts | Yes | Yes |
| Incremental SHA-256 synchronization and legacy workspace migration | Yes | Yes |
| Multiple root collections in one operation | One at a time | Yes |
| Dry-run, status, pruning, full verification, and workspace adoption | No | Yes |
| Diagnostics, named projects, saved configuration, and automation | No | Yes |
| Runs without Python or direct SQLite access | Yes | No |

Both interfaces produce the same managed workspace format. The plugin stays focused
and conservative; the CLI provides explicit administrative controls.

## Zotero 9 plugin

The plugin runs entirely inside Zotero. It does not require Python, Homebrew, pipx,
an executable path, temporary bridge files, or subprocesses.

Download the XPI from the [latest GitHub release](https://github.com/sbilmis/zotero-project-manager/releases/latest),
then open **Zotero → Tools → Plugins → gear menu → Install Plugin From File…**.
Existing installations can be upgraded in place.

Right-click a collection to use:

```text
Export with zpm
    Export Collection
    Export Collection + Annotations
    Settings…
```

Settings control:

- the default export folder;
- whether non-PDF attachments such as `README.md`, text, images, and data are included;
- attachment filename ordering;
- `separate`, `sidecar`, or `bundle` annotation layout.

The first export asks for a destination if no valid default exists. Zotero can install
future releases automatically when **Update Add-ons Automatically** is enabled in the
Plugins gear menu; **Check for Updates** provides a manual check.

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

A typical export looks like this:

```text
My-AI/
    Curie - 2024 - Paper title.pdf
    README.md
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

The manifest supports incremental exports:

- unchanged files are left alone;
- new and changed attachments are copied;
- missing or removed attachments are recorded without silently deleting prior copies;
- identical files re-added under a new Zotero key are reconciled;
- root-level manifest v1–v4 workspaces migrate under `.zpm/` after a successful export.

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

Build the reproducible Zotero XPI with:

```bash
.venv/bin/python scripts/build_zotero_plugin.py
```

See [CONTRIBUTING.md](CONTRIBUTING.md), [PUBLISHING.md](PUBLISHING.md), the
[plugin guide](zotero-plugin/README.md), and [CHANGELOG.md](CHANGELOG.md) for focused
development and release details.

Zotero Project Manager is released under the [MIT License](LICENSE).
