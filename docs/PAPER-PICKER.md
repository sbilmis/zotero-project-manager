# Choose Zotero papers from an Org note

The **1.3.0** adds an Emacs paper picker. A picker is a searchable
list: you can browse it without remembering a title, then select a paper.
It uses the collection currently selected in Zotero, or a collection remembered
in the current Org note. Zotero calls its folder-like entries **collections**.

## Install the Zotero plugin and Emacs module

1. Download/use the locally built
   `/Users/sbilmis/developer/projects/zotero-project-manager/dist/zpm-zotero-1.3.0.xpi`.
2. In **Zotero → Tools → Plugins → gear → Install Plugin From File…**, select that
   XPI. Install over the existing plugin and restart Zotero if prompted. Check that
   Zotero Project Manager shows **1.3.0**. Version 1.2.0 does not have the picker.
3. In **Zotero → Settings → Advanced**, enable **Allow other applications on this
   computer to communicate with Zotero**. The picker respects this setting and
   does not enable it automatically. No online account or API key is needed.
4. Install/load the Emacs module using **Emacs installation on another Mac or
   recovery** below. Installing the XPI alone does not install Emacs code.
   On sbilmis this step is already done: the managed/live module is installed
   and loaded in running Emacs. Existing link handlers, zotxt, and APA are
   preserved. No keybindings were added and neumann was not changed.

The owner installed pre1 and confirmed the picker works after enabling the
permission. Pre2 includes structured permission errors; the latest Emacs module
also recognizes pre1's permission error, so its help prompt works with either.
Stable 1.3.0 retains the tested preview behavior.

## If local access is disabled

When a picker command encounters the permission error, Emacs asks:

```text
Zotero local access is disabled. Show the steps to enable it? (y or n)
```

Type **y** to open ***ZPM Picker Setup***, a help buffer with the exact setting:
**Zotero → Settings → Advanced → Allow other applications on this computer to
communicate with Zotero**. This permits applications on your computer to read
Zotero library data. The plugin does not enable it for you. After you enable it,
return to the Org note and rerun the command; no restart is required.

Type **n** to dismiss the offer. Your note remains unchanged either way. Run
**M-x zpm-picker-setup** at any time to show the same help. Unrelated HTTP errors
remain ordinary errors and do not offer to enable this permission.

The Emacs client decodes Zotero responses as UTF-8. This fixes the previously
garbled arrows/quotes and preserves non-English author names and paper titles.

## Insert a link while writing

1. In Zotero's left sidebar, click a collection under **My Library**, for example
   **scientometry**. Leave Zotero running.
2. In Emacs, open your `.org` note and put the text cursor where the link belongs.
3. Press **M-x**, type **zpm-insert-paper-link**, and press Return. `M-x` means
   Option-x, or Escape followed by x. It runs a named Emacs command.
4. A list appears with each paper's authors, year, title, and unique Zotero key.
   Your Vertico setup displays candidates immediately. Use the up/down arrows
   to browse. Type an author, year, or words from a title to filter the list;
   Orderless, when installed, allows words in any order. Press Return to choose.
5. Emacs inserts a collection-specific Org link at the text cursor. For example:

```org
Compare this with [[zotero-item:ABCD2345?collection=6RIU3F76][Paper title]].
```

These example keys are illustrative. The picker supplies real keys automatically.
The list is fetched each time, so it reflects the library at request time. There
is no bibliography generation or dependency on zotxt. Duplicate titles remain
separate entries distinguished by their unique keys. Cancel with **C-g** to leave
text unchanged. Save the note using **M-x save-buffer**.

A fetch waits up to five seconds by default. Only papers directly in the collection
are listed, including all regular bibliographic types; notes, PDFs, other
attachments, and deleted entries are omitted. Subcollections are not expanded.
Open the relevant child collection if that is where a paper is filed.

To activate an inserted link, place the cursor on it and use **M-x
org-open-at-point**. It selects the paper record in its collection, without opening
a PDF. Expand the paper's attachments in Zotero when you want to read the PDF.
The existing Org link handlers from [the link guide](LINKS.md) must be installed.

## Open a paper without inserting text

From the Org note run **M-x zpm-open-paper**. Choose a paper from the same list.
Emacs selects that record in Zotero, leaving the note unchanged. Opening is
currently supported on macOS and uses `/usr/bin/open` asynchronously without a
shell. Reading the list and inserting links do not launch another application.

## Remember a collection for a particular note

While Zotero is showing the desired collection, return to your Org note and run
**M-x zpm-remember-collection**. Emacs adds a setting line:

```org
#+ZPM_COLLECTION: 6RIU3F76
```

This is an Org **keyword**, a file-wide setting. It stores the collection's key,
not its name, so renaming the collection does not change the key. Save the note.
Next time you open that note, both picker commands use its remembered collection,
even if Zotero is currently showing another one. Each note can remember its own
collection; the setting also works when you narrow the view to a heading.

Run **M-x zpm-remember-collection** again to replace it with Zotero's currently
selected collection. Run **M-x zpm-forget-collection** and save to return to following
Zotero's selection. These commands edit only the collection keyword in the Org
buffer and never save the note automatically. They preserve keyword examples
inside source/example blocks and all existing links.

If you delete the remembered collection, the picker reports that it is missing;
it never silently switches to another collection. Forget or replace the setting.
A paper removed from a collection may no longer be reachable through its old
collection-specific link. Ordinary item links remain available in Zotero's menu.

## Troubleshooting

- **Command not found:** load the module as described below or restart Emacs after
  applying its configuration. Open an Org note first.
- **Cannot reach Zotero:** open Zotero, confirm the plugin version, and check the
  Advanced setting above. The default local port is 23119. If you deliberately
  changed Zotero's port, use **M-x customize-variable → zpm-port** to match it.
- **Install the picker preview:** the running plugin predates the endpoint; install
  1.3.0 and restart Zotero if requested. Emacs configuration alone is insufficient.
- **Select a collection:** My Library itself, saved searches, and group libraries
  are unsupported. Select a personal collection or use a remembered collection.
- **No paper records:** that collection contains no direct regular records. Its
  subcollections may contain papers; choose one of those instead.
- **Invalid or duplicate ZPM_COLLECTION:** retain one valid keyword line, or run
  zpm-forget-collection and remember the collection again. No guessed keys are used.

## Emacs installation on another Mac or recovery

The reusable source is [zpm-org-picker.el](emacs/zpm-org-picker.el). On sbilmis:

- Managed module: `~/developer/projects/my_config/home/private_dot_emacs.d/private_lisp/zpm-org-picker.el`
- Live module: `~/.emacs.d/lisp/zpm-org-picker.el`
- Managed loader: `~/developer/projects/my_config/home/private_dot_emacs.d/private_lisp/init-org.el`
- Live loader: `~/.emacs.d/lisp/init-org.el`

Open the managed module with **M-x find-file**, put the reusable Lisp contents in
it, and save. In managed `init-org.el`, add the following once, before
`(provide 'init-org)`. Do not replace existing Zotero link handlers or zotxt settings:

```elisp
(with-eval-after-load 'org
  (require 'zpm-org-picker))
```

Save the loader. In macOS Terminal, review and apply only these two files:

```sh
chezmoi diff ~/.emacs.d/lisp/init-org.el ~/.emacs.d/lisp/zpm-org-picker.el
chezmoi apply ~/.emacs.d/lisp/init-org.el ~/.emacs.d/lisp/zpm-org-picker.el
chezmoi verify ~/.emacs.d/lisp/init-org.el ~/.emacs.d/lisp/zpm-org-picker.el
```

In Emacs, open an Org note, then use **M-x eval-expression** to evaluate
`(require 'zpm-org-picker)`.
For recovery after editing an already loaded module, run **M-x load-file** and
choose the live module. Do not evaluate the entire init-org file. Future startups
load the module after Org loads; the note keyword persists when you save the note.

## Optional Emacs settings

No completion package is required. The picker uses Emacs's built-in completion;
Vertico provides the list UI on sbilmis, and Orderless permits matching fragments
in any order. Keep your existing completion configuration.

Use **M-x customize-variable** for either option:

- **zpm-port**: default **23119**. Change this only if you changed Zotero's HTTP port.
- **zpm-request-timeout**: default **5** seconds. Increase for unusually slow/large
  collections. A request can wait up to this timeout before reporting a connection error.

In the Customize buffer, **Apply** changes the running session; **Apply and Save**
(or **Save for future sessions**) also persists it. If ChezMoi manages your saved
settings file, bring that intended change back into its managed source before
future applies. Alternatively, put `(setq zpm-port 23119 zpm-request-timeout 5)`
with your chosen values in managed init-org.el, save, review/apply only that file,
and evaluate only the new setting form. Do not change the example defaults unless needed.

Verify loading with **M-x eval-expression** and `(commandp 'zpm-insert-paper-link)`;
the result should be `t`. Inserted links also require the named `zotero-item:`
handler from the link guide; preserve your existing `zotero:`/zotxt registration
and APA setting. No new keybindings are needed.

## Technical scope and verification

The plugin registers `GET /zpm/papers` on Zotero's existing local HTTP server.
Without a query it reads the main window's selected collection; with
`?collection=KEY` it reads that exact personal-library collection. It returns only
schema version, collection name/key, and paper key/title/authors/year. It loads
item metadata as needed and returns all direct records without pagination limits.
It respects Zotero's local API permission, accepts only GET with the Emacs client
header, rejects browser-origin requests, and removes its endpoint when disabled.
There are no Zotero writes, exports, attachment reads, uploads, or bibliography calls.
The client uses loopback only, no proxy or cookies, and disallows redirects.

Automated checks cover current/remembered collection, missing/invalid keys, groups,
permission and request guards, excluded records, empty/large collections, endpoint
cleanup, HTTP failures, exact insertion and process arguments, duplicate titles,
cancellation, read-only notes, and persistence including narrowed buffers/examples.
The opening tests mock process calls and do not launch applications. The owner
confirmed the actual picker works after enabling local API permission. Automated
checks also exercise the UTF-8 fix and permission-help acceptance/decline.
Still manual: remember/save/reopen behavior, all filtering combinations, and
opening through zpm-open-paper. Earlier native Org links were already user-tested.

From the repository directory:

```sh
node --test zotero-plugin/tests/*.test.cjs
emacs --batch -Q -l zotero-plugin/tests/org-picker.test.el
emacs --batch -Q -l zotero-plugin/tests/org-links.test.el
.venv/bin/python -m pytest
python3 scripts/build_zotero_plugin.py --development
```

[Zotero local API settings and local-library access](https://www.zotero.org/support/dev/web_api/v3/local_api)
provide the underlying permission model. The bridge uses Zotero's installed server
endpoint API and `ZoteroPane.getSelectedCollection()` to capture UI context that
ordinary collection-data requests do not supply.
