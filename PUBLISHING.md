# Publishing

Python CLI releases use PyPI Trusted Publishing. No long-lived PyPI token is
stored in GitHub. The Zotero plugin is distributed as a GitHub release asset.

## One-time PyPI setup

Create a pending trusted publisher at <https://pypi.org/manage/account/publishing/>:

- PyPI project name: `zotero-project-manager`
- GitHub owner: `sbilmis`
- GitHub repository: `zotero-project-manager`
- Workflow: `publish.yml`
- Environment: `pypi`

Create a protected GitHub environment named `pypi` and require manual approval.

## Release checklist

1. Decide whether the release updates the plugin, Python CLI, or both. Update
   `zotero-plugin/manifest.json` for a plugin release; update `pyproject.toml` and
   `src/zotero_project_manager/__init__.py` for a CLI release. Do not bump an
   unchanged component solely to match the other component's version.
2. Update `CHANGELOG.md` and prepare `docs/releases/X.Y.Z.md` using the
   [release-note template](.github/RELEASE_TEMPLATE.md). Follow the editorial
   and publication checks below for every release, including patches and previews.
3. Run `pytest`, the plugin JavaScript tests, and build Python and XPI artifacts locally.
4. Add the plugin version, immutable release URL, and exact XPI SHA-256 to
   `zotero-plugin/updates.json`; rebuild to verify that the feed and artifact match.
5. Merge the release commit to `main` and create its signed or annotated version tag.
6. Publish a GitHub release titled **Zotero Project Manager (ZPM) X.Y.Z** from that
   tag. Use the reviewed release-note file as its body and attach the exact
   verified, versioned XPI when the plugin changes. Do not use an automatically
   generated commit list as the entire release note.
7. For a CLI release, approve the protected `pypi` deployment after CI succeeds.
   For a plugin-only release, ensure the publish workflow skips PyPI before
   publishing the GitHub release; never submit an already published CLI version.
8. For a plugin release, start from the previous plugin version, run **Tools →
   Plugins → gear → Check for Updates**, and verify that Zotero installs the new
   version.
9. For a CLI release, update `sbilmis/homebrew-tap` to the new PyPI source archive and dependency
   resources, then verify `brew audit`, `brew style`, and the formula test.
10. For a plugin release, verify that the existing Add-on Market listing refreshes
    after publication. Initial registration only: add
    `addons/sbilmis@zotero-project-manager` to `syt2/zotero-addons-scraper` with up
    to two supported tags; subsequent releases do not need another submission.

The current `.github/workflows/publish.yml` runs for every published GitHub
release, builds Python artifacts, and authenticates to PyPI using a short-lived
OpenID Connect token. It does not yet distinguish plugin-only releases: add and
verify that guard before publishing a plugin-only release such as 1.4.0.

## Release-note standard

Keep a concise historical entry in `CHANGELOG.md` and the complete user-facing
notes in `docs/releases/X.Y.Z.md`. The latter is the source for the GitHub release
body. The [1.4.0 draft](docs/releases/1.4.0.md) is an example.

Every release note must answer:

- What changed, and who benefits? Describe observable behavior rather than a
  list of implementation commits; distinguish new features from existing ones.
- Which plugin, Zotero, CLI, and Emacs versions or setup steps are affected?
  State explicitly when an independently versioned component is unchanged.
- How does an existing user upgrade? Include the artifact name or update
  command, restart needs, and any workspace or configuration migration.
- What limitations or breaking changes matter? Explain export direction and
  effects on edited output files when relevant.
- What was actually verified? Separate automated tests, live checks, and
  unverified environments. Do not turn a planned check into a completed claim.

Before publishing:

1. Review the notes against the final diff, packaged manifest, update feed, and
   CI results. Finish required manual checks or explicitly document any remaining
   limitation before deciding that the release is ready.
2. Replace the draft status with the actual release date, or clearly label a
   prerelease. Remove placeholders and future-tense installation instructions.
3. Convert relative links in the GitHub release body to absolute links pinned to
   the release tag. Check that documentation and download links resolve; keep
   relative links in the repository copy.
4. Render the draft on GitHub and check headings, tables, code, and links. Pass
   the prepared body to `gh release create` or `gh release edit` with `--notes-file`
   so formatting and newlines are preserved.
5. Verify the published title, notes, assets, and update path. Keep the repository
   notes and GitHub body in sync if a factual correction is needed.

## Plugin distribution

The companion plugin is self-contained; its runtime does not require the Python CLI.
It has an independent version in `zotero-plugin/manifest.json`. Build it with
`python scripts/build_zotero_plugin.py`, compute the XPI SHA-256, and update
`zotero-plugin/updates.json` before tagging the release. The build intentionally fails
when the feed does not contain the exact artifact hash, while still leaving the newly
built XPI in `dist/` so its hash can be copied into the feed.
Keep previous compatible entries in the update feed so both clean installations and
older installed versions have a complete upgrade path. The update link must name the
XPI attached to the matching GitHub release, and the hash must be computed from that
exact artifact. Zotero checks the manifest's update URL using its normal add-on update
mechanism, so no plugin-specific updater or external executable is needed.

The Add-on Market scraper reads public GitHub releases. Submit its registry entry
only after the matching release exists and contains the versioned XPI asset.
