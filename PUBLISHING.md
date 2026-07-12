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
3. Run `pytest` and build both distributions locally.
4. Merge the release commit to `main` and create its signed or annotated version tag.
5. Publish a GitHub release from that tag.
6. Approve the protected `pypi` deployment after CI succeeds.

Publishing the GitHub release triggers `.github/workflows/publish.yml`, which builds
fresh artifacts and authenticates to PyPI using a short-lived OpenID Connect token.

