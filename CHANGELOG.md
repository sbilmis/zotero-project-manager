# Changelog

All notable changes are documented here. This project follows semantic versioning.

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
