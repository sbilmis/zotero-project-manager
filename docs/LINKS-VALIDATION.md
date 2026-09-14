# Native link preview: change and validation record

Local development preview: **1.2.0pre2**, 2026-09-14.

## Changed files

Repository files, relative to
`/Users/sbilmis/developer/projects/zotero-project-manager`:

- `zotero-plugin/links.js`: formatting, validation, clipboard commands, library
  and PDF reader menus, plugin-specific cleanup.
- `zotero-plugin/bootstrap.js`, `zotero-plugin/zpm.js`: load and manage link menus
  under one Zotero Project Manager menu. Export implementation unchanged.
- `zotero-plugin/locale/en-US/zpm.ftl`: collection/item/PDF and batch command labels.
- `zotero-plugin/manifest.json`: identifiable local prerelease version/description.
- `scripts/build_zotero_plugin.py`: include the new module in the XPI.
- `.github/workflows/ci.yml`: syntax-check the module and build development XPIs
  without requiring a published release feed entry. Strict release verification
  remains in the build script; `updates.json` is unchanged.
- `zotero-plugin/tests/links.test.cjs`: validation, native menus, reader hooks,
  lifecycle, packaged bootstrap loading, and copying tests.
- `zotero-plugin/tests/org-links.test.el`: real Org dispatch with process stubs.
- `zotero-plugin/tests/standard-menu.test.cjs`: exercise existing export commands
  through the consolidated menu.
- `tests/test_plugin_package.py`: check the new packaged module and its loader.
- `docs/emacs/zpm-org-links.el`: reusable tested handler block.
- `docs/LINKS.md`, `docs/LINKS-VALIDATION.md`, `README.md`,
  `zotero-plugin/README.md`: usage, installation, compatibility, checks, and scope.

Requested external files:

- `/Users/sbilmis/developer/projects/my_config/home/private_dot_emacs.d/private_lisp/init-org.el`
- `/Users/sbilmis/.emacs.d/lisp/init-org.el` (only this live ChezMoi target applied)
- `/Users/sbilmis/sb_org/reference/runbooks/zotero-org-collection-links.org`

The repository was initially clean. Existing changes in the separate my_config
repository were preserved. A before/after comparison excluding the affected
handler block confirmed that all other content in init-org.el is unchanged.
The pre-existing zotxt instructions and APA diagnostic history in the runbook
are byte-for-byte preserved under its historical section.

## Automated and configuration checks actually completed

- **87 Python tests passed**, including existing exports and XPI packaging.
- **40 JavaScript tests passed**, including twelve link tests. Coverage includes
  label brackets/newlines/Unicode/Markdown punctuation, missing and invalid
  keys, single and mixed batch selections, unsupported types/libraries, atomic
  rejection without changing the clipboard, exact page/annotation destinations,
  native clipboard dispatch, menu enablement, plugin cleanup, and bootstrap
  startup/shutdown with the real packaged modules.
- **6 Emacs ERT tests passed** against each of the reusable example, managed
  configuration, and applied live configuration. Real `org-open-at-point`
  dispatch was exercised; `start-process` was stubbed to assert the exact process
  name, nil buffer, `/usr/bin/open`, and separate URI argument. No application
  was launched by these tests. Invalid paths raise user errors before any process
  call. Deferred registration and existing `zotero:` registration were tested.
- Syntax checks passed for bootstrap, links, zpm, preferences, and native exporter.
- `git diff --check` passed.
- The precise file-specific ChezMoi diff was reviewed before apply. ChezMoi verify
  passed afterward, and the managed and live files match.
- Only the four affected function definitions and Org registration form were
  evaluated in running Emacs. Registration returned the named collection/item/PDF
  handlers; `zotero:` still points to `org-zotxt--link-follow`, and the style
  remains `apa`. The existing init.el requires init-org for future startups.
- URI routes, key alphabet, clipboard API, and reader context were checked against
  the installed Zotero source and current upstream source linked in LINKS.md.
- The development XPI built successfully; ZIP integrity and packaged file checks
  passed. The release feed was not changed.

## Artifact and manual checks

XPI:
`/Users/sbilmis/developer/projects/zotero-project-manager/dist/zpm-zotero-1.2.0pre2.xpi`

SHA-256:
`4b546e5138a9c6cf1f3f68c510bfc1928b7538060548d6fdf813dc8405831ff8`

Follow [LINKS.md](LINKS.md) to install and test. Still manual: actual Zotero menu
rendering/enabling, clipboard paste, collection/record/PDF/page/annotation opening,
Obsidian link activation, sync/file availability, and a GUI export smoke test.
The new XPI has deliberately not been installed, so no real Zotero plugin-runtime
or end-to-end GUI success is claimed. An Emacs restart was not performed; startup
persistence was checked by source inspection and deferred-registration tests.

For PDFs to open in Zotero's reader, the user must select Zotero in
**Settings → General → Open PDFs using**. Zotero's standard `open-pdf` URI honors
that preference; these commands do not change it. Page links use physical page
numbers, not printed page labels. Multiple collections/pages/annotations are
unsupported; batch copying covers selected paper records and PDF attachments.

No release published, XPI installed, neumann changes, library modifications,
new keybindings, or keyboard-shortcuts documentation changes were made.

## Follow-up: consolidated menus and collection context

- One Zotero Project Manager parent per library context menu; Copy Link formats,
  collection-only Export, and Settings have short labels. Item menus switch
  between single and multiple copying and hide inapplicable collection context.
- Copy Link in This Collection is optional for one regular paper directly in
  the selected personal-library collection. It encodes both validated keys.
  It never guesses among the paper's collections; ordinary item links are unchanged.
- Org syntax: `[[zotero-item:ABCD2345?collection=6RIU3F76][Paper title]]`.
  Markdown/URI target:
  `zotero://select/library/collections/6RIU3F76/items/ABCD2345`.
- Tests cover direct membership, both keys, unsupported contexts, all formats,
  contextual visibility, exact Org activation arguments, and invalid queries.
- Only the existing item handler was changed in init-org.el for this follow-up.
  Its precise ChezMoi diff was reviewed, only that live file was applied and
  verified, and only the changed function was evaluated in running Emacs.
- The user verified ordinary Org item activation with the earlier preview.
  The consolidated menus and new collection-specific activation still need
  a manual check after installing pre2. This task did not install pre2.

## Stable 1.2.0 release preparation

The user confirmed the pre2 menus are neat and both ordinary My Library item
links and Copy Link in This Collection work, and authorized publishing.
Stable 1.2.0 retains the tested plugin code. All 87 Python, 40 JavaScript, and
six Emacs tests were rerun successfully. The stable XPI was built and its
versioned URL and exact SHA-256 added to updates.json; strict rebuild passed.
CI now performs strict release-feed verification again. The Python package is
versioned 1.2.0 consistently with the release; CLI behavior is unchanged.
Earlier statements above about unpublished previews describe those earlier stages.
