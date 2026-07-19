# Publishing

Releases use PyPI Trusted Publishing. No long-lived PyPI token is stored in GitHub.

## One-time PyPI setup

Create a pending trusted publisher at <https://pypi.org/manage/account/publishing/>:

- PyPI project name: `zotero-project-manager`
- GitHub owner: `sbilmis`
- GitHub repository: `zotero-project-manager`
- Workflow: `publish.yml`
- Environment: `pypi`

Create a protected GitHub environment named `pypi` and require manual approval.

## Release checklist

1. Update the version in `pyproject.toml` and `src/zotero_project_manager/__init__.py`.
2. Update `CHANGELOG.md`.
3. Run `pytest`, the plugin JavaScript tests, and build Python and XPI artifacts locally.
4. Add the plugin version, immutable release URL, and exact XPI SHA-256 to
   `zotero-plugin/updates.json`; rebuild to verify that the feed and artifact match.
5. Merge the release commit to `main` and create its signed or annotated version tag.
6. Publish a GitHub release from that tag and attach the exact verified, versioned XPI.
7. Approve the protected `pypi` deployment after CI succeeds.
8. From an installation of the previous plugin version, run **Tools → Plugins →
   Check for Updates** and verify that Zotero installs the new version.
9. Update `sbilmis/homebrew-tap` to the new PyPI source archive and dependency
   resources, then verify `brew audit`, `brew style`, and the formula test.
10. Submit the released plugin to `syt2/zotero-addons-scraper` by adding
    `addons/sbilmis@zotero-project-manager` with up to two supported tags.

Publishing the GitHub release triggers `.github/workflows/publish.yml`, which builds
fresh artifacts and authenticates to PyPI using a short-lived OpenID Connect token.

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
