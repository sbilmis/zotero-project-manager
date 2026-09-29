# Set up Zotero links and the Emacs paper picker

This setup is for **macOS**. The supplied Org link handlers and
`zpm-open-paper` use macOS to open Zotero. Once installed, follow the
[quick start](QUICKSTART.md).

## 1. Install ZPM in Zotero

Follow [Install ZPM](PLUGIN-QUICKSTART.md#1-install-zpm) in the plugin quick start.
Zotero 10 requires **ZPM 1.3.2 or newer**; 1.3.2 also supports Zotero 9.

Installing the Zotero plugin does not install the Emacs files. Python, Homebrew,
and zotxt are not required for these linking features.

## 2. Load the Emacs files

Download both files using GitHub's **Raw / Download raw file** control:

- [zpm-org-links.el](emacs/zpm-org-links.el): opens Org links to Zotero.
- [zpm-org-picker.el](emacs/zpm-org-picker.el): supplies the five picker commands.

Save them in a `lisp` directory inside your Emacs configuration directory
(`user-emacs-directory`), commonly `~/.emacs.d/lisp/`. Create the directory if
needed. Make sure the saved files contain Lisp code, not a GitHub HTML page.

Add this block once to your Emacs init file:

```elisp
(let ((zpm-directory (expand-file-name "lisp/" user-emacs-directory)))
  (add-to-list 'load-path zpm-directory)
  (load (expand-file-name "zpm-org-links.el" zpm-directory) nil t)
  (with-eval-after-load 'org
    (require 'zpm-org-picker)))
```

Restart Emacs, then open an Org note. If you previously copied ZPM's link-handler
functions into your configuration, use this file loader in place of that copied
block. Keep your existing zotxt, bibliography, and completion settings.
If a dotfile manager maintains your init file, edit and apply its source as usual.

## 3. Allow the picker to read Zotero

In **Zotero → Settings → Advanced**, enable **Allow other applications on this
computer to communicate with Zotero**. This allows local applications to read
your Zotero library. No online API key is needed, and ZPM does not change the
setting for you. It is needed for the picker; copying links from Zotero's menus
does not require it.

Select one collection under **My Library**, leave Zotero open, and run
**M-x zpm-insert-paper-link** in your Org note. Pick a paper and open its link
with **C-c C-o**. You are ready for the [quick start](QUICKSTART.md).

## If something does not work

| Symptom | What to check |
| --- | --- |
| `zpm-insert-paper-link` is missing | Open an Org note; check the file locations and loader block, then restart Emacs |
| Local access is disabled | Enable the Advanced setting above and retry; no Zotero restart is needed |
| Cannot reach Zotero | Keep Zotero running and confirm ZPM is enabled |
| Picker endpoint not found | Update ZPM using the latest release and restart Zotero if prompted |
| Select a collection / no paper records | Choose one personal-library collection containing papers directly, rather than My Library itself or a saved search |
| Org does not open the inserted link | Confirm `zpm-org-links.el` was loaded; the supplied handlers require macOS |
| PDF opens in another reader | Set **Zotero → Settings → General → Open PDFs using → Zotero** |

Run **M-x zpm-picker-setup** to show connection help inside Emacs. If Emacs offers
this help after a permission error, accepting it opens instructions; it does not
change Zotero settings.

The optional Emacs variables `zpm-port` (default **23119**) and
`zpm-request-timeout` (default **5** seconds) are available through
**M-x customize-variable**. Change the port only if you changed Zotero's port.
No completion package is required; Vertico and Orderless are optional.
