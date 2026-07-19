# Changelog

All notable changes are documented here. This project follows semantic versioning.

## 1.0.0 — 2026-07-19

- Make Zotero plugin 1.0.0 completely self-contained: exports now run through a
  native JavaScript engine with no Python, Homebrew, pipx, executable path, temporary
  bridge file, or subprocess requirement.
- Retain the Python `zpm` CLI as an independent interface for terminal automation,
  scheduled exports, safe pruning, full verification, and direct SQLite workflows.
- Export non-PDF Zotero attachments, including `README.md`, through a plugin setting
  while limiting generated PDF annotation documents to PDF attachments.
- Move manifests, metadata, indexes, and summaries under `.zpm/` so user attachments
  can safely use ordinary project filenames; migrate root-level manifest v1–v4
  workspaces after a successful export.
- Preserve portable filename presets, recursive collection layouts, incremental
  SHA-256 synchronization, re-added-file reconciliation, annotation layouts, cached
  image assets, notes, DOI/tag metadata, and unmanaged-file protections in JavaScript.
- Simplify the collection menu to export actions and Settings, and remove executable
  selection and installation diagnostics from the Zotero UI.
- Document Zotero-managed automatic plugin updates with manual checking as a fallback.
- Expand cross-interface coverage to 72 Python tests and 12 native-plugin tests,
  including Markdown collisions, legacy migration, symlink escapes, and control-file
  ownership checks.

## 0.9.0 — 2026-07-14

- Add `separate`, `sidecar`, and `bundle` annotation workspace layouts for direct
  exports, plugin exports, global configuration, and named projects.
- Record the layout in manifest v4 and reject unsafe in-place layout changes while
  retaining compatible defaults for manifest v1–v3 workspaces.
- Add a Zotero 9 settings pane for the default output folder, custom zpm executable,
  installation testing, and annotation-layout selection.
- Add a collection-menu **Settings…** shortcut and preserve automatic Homebrew/PATH
  executable discovery in both the export flow and settings test.
- Add Zotero plugin 0.2.0 with a versioned SHA-256 update-feed entry so installed
  plugin 0.1.0 copies can update through Zotero's plugin manager.
- Expand Python and JavaScript coverage for layout structures, configuration,
  manifests, snapshot exports, collisions, and command arguments.

## 0.8.0 — 2026-07-14

- Add the optional Zotero 9 companion plugin with collection context-menu commands
  for PDF export, PDF plus annotation export, output and executable selection, and
  installation checks.
- Add a validated, size-bounded plugin snapshot bridge so exports initiated inside
  Zotero never open `zotero.sqlite` and are unaffected by SQLite locks.
- Keep all copying, filename, manifest, metadata, annotation, and safety behavior in
  the Python exporter instead of duplicating it in the plugin.
- Export cached Zotero image and ink annotation previews as managed PNG assets and
  embed them in the generated Markdown without writing to Zotero's cache.
- Restrict plugin-provided image paths to PNG files inside Zotero's cache and protect
  exported asset folders with zpm safety markers.
- Expand `zpm doctor` with stable check identifiers, JSON output, Zotero application
  and runtime detection, attachment availability counts, configuration reporting,
  and more actionable output safety checks.
- Bound SQLite snapshot attempts to prevent indefinite waits when Zotero is busy.
- Add Python bridge/diagnostic tests, dependency-free JavaScript plugin tests, a
  reproducible XPI builder, and a dedicated Zotero 9 CI job.

## 0.6.0 — 2026-07-13

- Add opt-in `--annotations` export for PDF highlights, underlines, comments,
  colors, page labels, annotation tags, image/ink metadata, and child notes.
- Generate safe, hierarchy-preserving Markdown under `Annotations/`, including
  links to exported files and local-library Zotero items.
- Convert Zotero child-note HTML into dependency-free, readable Markdown text.
- Refuse to replace unmanaged annotation Markdown and update generated files only
  when their content changes.
- Add filename ordering presets covering every author/year/title permutation, plus
  shorter author/title, year/title, title/author, title/year, and title-only forms.
- Support filename preferences in direct exports, global configuration, and named projects.
- Add manifest v3 to record the workspace filename template and prevent accidental
  in-place reorganization of an existing managed workspace.

## 0.5.0 — 2026-07-12

- Read DOI and tag metadata directly from Zotero without modifying its database.
- Generate machine-readable `metadata.json` for current active and missing attachments.
- Generate a linked `INDEX.md` table with titles, creators, years, DOI, tags, and files.
- Add metadata generation to direct exports and named projects, enabled by default.
- Add `--no-metadata` for workspaces that do not want generated metadata artifacts.
- Refuse to replace existing `metadata.json` or `INDEX.md` files unless they carry zpm's
  generated-file marker.

## 0.4.0 — 2026-07-12

- Add dependency-free TOML configuration with XDG and `ZPM_CONFIG` path support.
- Add `zpm config set` and `zpm config show` for global Zotero, output, and linked-file defaults.
- Add reusable named projects through `zpm project add`, `list`, and `show`.
- Add `zpm sync NAME` for one-command synchronization of saved collection groups.
- Resolve relative configured paths from the configuration file directory.
- Write configuration atomically and reject malformed settings with actionable errors.

## 0.3.0 — 2026-07-12

- Add cross-platform CI for Python 3.11 and 3.14.
- Build and validate source and wheel distributions on every pull request and main push.
- Add release-gated PyPI Trusted Publishing with no stored API token.
- Document `pipx` installation and the protected release process.
- Add canonical project, documentation, issue, and changelog URLs to package metadata.

## 0.2.1 — 2026-07-12

- Explain that Zotero may remain open unless it holds an exclusive database lock.
- Replace raw SQLite lock failures with instructions to wait for Zotero activity
  to finish or close Zotero before retrying.
- Guarantee the lock message states that `zpm` used read-only access and made no changes.

## 0.2.0 — 2026-07-12

### Added

- `zpm status` for a completely read-only synchronization preview.
- Safe `--prune` support for attachments removed from Zotero.
- SHA-256 digests in manifest v2 and full `--verify` checks.
- Reconciliation of identical attachments re-added under a new Zotero key.
- Manifest states for active, missing, and removed attachments.
- `zpm doctor` diagnostics for Zotero, SQLite, storage, linked files, and output paths.
- Counts and detailed actions for removed, pruned, protected, and reconciled files.

### Safety

- Pruning only deletes a manifest-owned file whose current content matches its trusted hash.
- Modified, unverifiable, symlinked, or unsafe manifest destinations are protected.
- Existing manifest v1 files migrate automatically in memory and are written as v2 only after
  a successful non-dry-run synchronization.

## 0.1.0 — 2026-07-12

- Initial release with read-only Zotero access, recursive multi-collection export,
  incremental copying, portable filenames, manifests, and generated workspace READMEs.
