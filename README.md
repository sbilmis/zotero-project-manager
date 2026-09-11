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

Exports run inside Zotero and do not require Python, Homebrew, pipx, or an
executable path. The optional macOS app handoffs use built-in AppleScript with
short-lived temporary manifests; ordinary exports do not launch subprocesses.

Download the XPI from the [latest GitHub release](https://github.com/sbilmis/zotero-project-manager/releases/latest),
then open **Zotero → Tools → Plugins → gear menu → Install Plugin From File…**.
Existing installations can be upgraded in place.

Right-click a collection to use:

```text
Export with zpm
    Export Collection
    Export Collection + Annotations
    Send to Gemini Notebook…
    Set Gemini Notebook Link…
    Send to DEVONthink 4…
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

## Send to Gemini Notebook or DEVONthink

The two destinations are independent. In Zotero, right-click a collection and
choose either **Send to Gemini Notebook…** or **Send to DEVONthink 4…**.
Both actions export the collection with notes and annotations first.

- **Gemini Notebook** opens the saved notebook for this collection and reveals the
  prepared sources. On first use, paste a notebook URL to remember it, or leave the
  prompt blank to open the home page. On macOS, the exact source files are selected
  in Finder. Open or create a notebook if you have not linked one yet,
  and drag those files into **Add sources**, or use **Upload files**. The final upload
  is manual; no Chrome extension, API key, or Google Drive setup is required.
- **DEVONthink 4** (macOS) asks you to choose a database/group, then indexes the exported
  files under a collection group, preserving subfolders. Indexed files stay in the
  export folder. Sending again refreshes existing records and adds newly exported
  files without duplicating already indexed paths in that database. Existing records
  keep their DEVONthink location; this action does not move or delete old records.
  The handoff targets DT4 explicitly by bundle ID and never falls back to DT3,
  even when both versions are installed.

The CLI provides the same two destinations:

```bash
zpm export "My-AI" --output ~/ResearchProjects --to gemini-notebook
zpm export "My-AI" --output ~/ResearchProjects --to devonthink --annotations
```

Use `--notebook-url https://notebook.google.com/notebook/…` to open a specific
notebook, or `--devonthink-group UUID` to select a DEVONthink group without its
chooser. `--prepare-only` exports without opening apps. `--dry-run` neither
writes files nor opens apps. CLI notes and annotations remain opt-in except when
using the Notebook profile, which includes them.

Keep DEVONthink exports in a permanent folder: it makes copies of temporary files
instead of indexing them. The export folder remains necessary after indexing.
Zotero originals remain untouched. Changes in Zotero reach DEVONthink after you
export/send again; there is no continuous Zotero watcher.

Only files from the current export are handed off, excluding zpm bookkeeping,
unmanaged personal files, and old retained attachment copies. Gemini Notebook
uploads are snapshots: repeat uploads can create duplicate sources, and zpm does
not verify Google's processing. Check the notebook's Sources panel after uploading.

### Remember a notebook for a collection

Create/open your notebook once in the browser and copy its address. In Zotero,
right-click the collection and choose **Export with zpm → Set Gemini Notebook
Link…**, paste the URL, and press **OK**. Later **Send to Gemini Notebook…**
actions open that notebook directly. The first Send also asks for a link when
none is saved.

- Links are local Zotero preferences, keyed by library ID and collection key:
  restarting Zotero or renaming a collection does not lose its link. Same-named
  collections can point to different notebooks. Links are not synced to other Macs.
- Use **Set Gemini Notebook Link…** again to change the URL. Submit an empty value
  to forget it; **Cancel** preserves it. Forgetting a link does not delete anything
  from Google. Cancelling a first-send prompt stops the handoff, not the completed
  export.
- Only direct HTTPS notebook URLs on Google's supported Notebook hosts are
  accepted. Account selectors in the URL are retained; tracking parameters and
  fragments are removed. The plugin does not log in, detect account ownership,
  or verify access: select the correct Google account in your browser.
- Creation, naming, and uploads remain manual. Saving a link alone does not open
  apps or send files. The CLI retains its independent `--notebook-url` option and
  does not read the plugin's saved preferences.

See [the Agentic_AI test guide](docs/TESTING.md) for installation, repeat-send,
restart, change-link, and clear-link checks.

### Future Notebook automation and API delivery

Further options are tracked in [PROJECT.org](PROJECT.org):

- Offer browser-assisted creation with the collection name.
  The [reference Chrome connector](https://github.com/peterdresslar/zotero-gemini-notebook)
  documents notebook creation, but collection naming and zpm integration still need
  validation. A genuine upload click can remain necessary; retain manual fallback
  when the browser UI changes or an upload's completion is uncertain.
- Optionally evaluate Drive-linked sources for repeat updates. Google's
  [Drive import documentation](https://support.google.com/gemininotebook/answer/16215270?hl=en)
  describes updates to imported sources, not automatic notebook creation or
  watching a folder for new sources. Test Drive file identity across re-exports.

**API migration condition:** if an official Notebook API is available to the
user's account and approved for use, add an API delivery adapter while retaining
source preparation and the manual fallback. Validate account scope, formats,
notebook/source IDs, upload status, and safe retries before switching.

As checked on 2026-09-10, Google already documents preview Enterprise APIs for
[notebook creation](https://docs.cloud.google.com/gemini/enterprise/notebooklm-enterprise/docs/api-notebooks)
and [file uploads](https://docs.cloud.google.com/gemini/enterprise/notebooklm-enterprise/docs/api-notebooks-sources).
Enterprise setup/licensing is required; this is not an integration unlocked simply
by providing a normal Gemini API key. This project has not connected those APIs.

These are roadmap options, not features included in the current preview.

### Prepare a notebook folder without opening apps

Use the `notebooklm` profile to prepare a collection without starting the handoff:

```bash
zpm export "My-AI" --output ~/ResearchProjects --profile notebooklm
```

The **Send to Gemini Notebook…** action produces the same layout before opening
the apps. Each collection gets a separate `My-AI - NotebookLM/` workspace containing:

- a flat set of supported document, image, and audio attachments;
- one sidecar Markdown annotation file per PDF;
- a generated `collection-overview.md` source guide;
- hidden `.zpm/` bookkeeping that should not be imported.

Use **Gemini Notebook → Add sources → Upload files** for local files. A Google
Drive-synced output directory and **Add sources → Google Drive** are also an option.
New sources still need to be selected in Gemini Notebook. zpm warns above 50 prepared
sources as a conservative reminder to check your plan's current source allowance.

Save the profile for repeatable CLI synchronization with:

```bash
zpm project add ai-notebook "My-AI" --profile notebooklm --output ~/ResearchProjects
zpm sync ai-notebook
```

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

Build the local preview XPI with:

```bash
.venv/bin/python scripts/build_zotero_plugin.py --development
```

Install `dist/zpm-zotero-1.1.0pre4.xpi` using Zotero's **Tools → Plugins → gear →
Install Plugin From File…**. This preview is not yet on the public update feed.
The installed Homebrew/pipx release does not change when this checkout changes;
use `.venv/bin/python -m zotero_project_manager` to run the CLI from this checkout.
Release builds omit `--development` and continue to verify update-feed hashes.

See [CONTRIBUTING.md](CONTRIBUTING.md), [PUBLISHING.md](PUBLISHING.md), the
[plugin guide](zotero-plugin/README.md), and [CHANGELOG.md](CHANGELOG.md) for focused
development and release details.

Zotero Project Manager is released under the [MIT License](LICENSE).
