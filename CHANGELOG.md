# Changelog

All notable changes are documented here. This project follows semantic versioning.

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
