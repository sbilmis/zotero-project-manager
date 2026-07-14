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
4. Merge the release commit to `main` and create its signed or annotated version tag.
5. Publish a GitHub release from that tag and attach the versioned XPI.
6. Approve the protected `pypi` deployment after CI succeeds.
7. From an installation of the previous plugin version, run **Tools → Plugins →
   Check for Updates** and verify that Zotero installs the new version.

Publishing the GitHub release triggers `.github/workflows/publish.yml`, which builds
fresh artifacts and authenticates to PyPI using a short-lived OpenID Connect token.

The companion plugin has an independent version in `zotero-plugin/manifest.json`.
Build it with `python scripts/build_zotero_plugin.py`, compute the XPI SHA-256, and
update `zotero-plugin/updates.json` before tagging the release.
Keep previous compatible entries in the update feed so both clean installations and
older installed versions have a complete upgrade path. The update link must name the
XPI attached to the matching GitHub release, and the hash must be computed from that
exact artifact.
