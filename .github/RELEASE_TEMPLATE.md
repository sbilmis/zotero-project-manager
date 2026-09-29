<!--
Copy to docs/releases/vX.Y.Z.md for every release, including patch releases and
previews. Replace every placeholder and remove these comments. Keep the notes
proportionate to the change; remove empty or irrelevant sections. Do not claim
support or verification without evidence. Follow PUBLISHING.md before publishing.
-->
# Zotero Project Manager (ZPM) X.Y.Z

**Status:** Draft / Prerelease / Released YYYY-MM-DD

One or two sentences explaining the main user benefit and who should upgrade.

## What's new

- **User-facing change.** Explain the resulting behavior, with a short example or
  menu path where useful. Group related changes and omit internal commit noise.

## Fixes

- Explain the symptom, when it occurred, and the corrected behavior.

## Compatibility and upgrade

| Component | Supported version / change |
| --- | --- |
| Zotero plugin | Plugin version and supported Zotero versions |
| Python CLI | CLI version, supported Python versions if changed, or explicitly unchanged |
| Exported workspaces | Migration requirements and effect on existing files/settings |
| Markdown/Org links and Emacs | Required setup changes, or explicitly none |

Give the exact update menu or command, versioned artifact name, restart needs,
and any required migration steps. Distinguish unpublished previews from updates
already offered to users. Link to detailed instructions where needed.

## Behavior and limitations

Describe breaking changes, known issues, and relevant boundaries. For export
changes, state the direction of synchronization and effects on edited output
files. Include recovery steps where practical. Do not imply bidirectional sync
unless it is implemented and verified.

## Verification

Summarize the automated checks and actual live environments verified. Identify
pending or unverified checks honestly. Keep detailed logs in the PR or CI.

## Guides

Link to the relevant quick start, changelog, and issue tracker. Use relative
links in the repository draft; convert them to absolute links pinned to the
release tag when preparing the GitHub release body.
