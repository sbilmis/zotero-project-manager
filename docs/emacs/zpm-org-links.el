;;; zpm-org-links.el --- Native Zotero links for Org -*- lexical-binding: t; -*-

(defun sb/org-zotero-key (key)
  "Validate a My Library Zotero KEY, returning it or raising a user error."
  (unless (and (stringp key)
               (let ((case-fold-search nil))
                 (string-match-p "\\`[23456789ABCDEFGHIJKLMNPQRSTUVWXYZ]\\{8\\}\\'" key)))
    (user-error "Invalid Zotero key: expected eight uppercase Zotero characters (no 0, 1, O)"))
  key)

(defun sb/org-open-zotero-collection (key _arg)
  "Open the Zotero collection identified by KEY on macOS."
  (start-process "zotero-collection" nil "/usr/bin/open"
                 (concat "zotero://select/library/collections/" (sb/org-zotero-key key))))

(defun sb/org-open-zotero-item (path _arg)
  "Select a Zotero paper PATH, optionally inside its copied collection."
  (unless (and (stringp path)
               (let ((case-fold-search nil))
                 (string-match
                  "\\`\\([23456789ABCDEFGHIJKLMNPQRSTUVWXYZ]\\{8\\}\\)\\(?:?collection=\\([23456789ABCDEFGHIJKLMNPQRSTUVWXYZ]\\{8\\}\\)\\)?\\'"
                  path)))
    (user-error "Invalid Zotero item link: expected KEY or KEY?collection=KEY"))
  (let ((key (match-string 1 path))
        (collection (match-string 2 path)))
    (start-process "zotero-item" nil "/usr/bin/open"
                   (if collection
                       (concat "zotero://select/library/collections/" collection "/items/" key)
                     (concat "zotero://select/library/items/" key)))))

(defun sb/org-open-zotero-pdf (path _arg)
  "Open a Zotero PDF PATH, optionally at a physical page and annotation."
  (unless (and (stringp path)
               (let ((case-fold-search nil))
                 (string-match
                  "\\`\\([23456789ABCDEFGHIJKLMNPQRSTUVWXYZ]\\{8\\}\\)\\(?:?page=[1-9][0-9]*\\(?:&annotation=[23456789ABCDEFGHIJKLMNPQRSTUVWXYZ]\\{8\\}\\)?\\)?\\'"
                  path)))
    (user-error "Invalid Zotero PDF link: expected KEY, KEY?page=N, or KEY?page=N&annotation=KEY"))
  (start-process "zotero-pdf" nil "/usr/bin/open"
                 (concat "zotero://open-pdf/library/items/" path)))

(with-eval-after-load 'org
  (when (eq system-type 'darwin)
    (org-link-set-parameters "zotero-collection"
                             :follow #'sb/org-open-zotero-collection)
    (org-link-set-parameters "zotero-item"
                             :follow #'sb/org-open-zotero-item)
    (org-link-set-parameters "zotero-pdf"
                             :follow #'sb/org-open-zotero-pdf)))

;;; zpm-org-links.el ends here
