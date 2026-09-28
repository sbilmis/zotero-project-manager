;;; zpm-org-picker.el --- Browse Zotero collections from Org -*- lexical-binding: t; -*-
(require 'org)
(require 'org-element)
(require 'json)
(require 'url-http)
(require 'cl-lib)
(defvar url-http-response-status)

(defgroup zpm nil "Zotero Project Manager note tools." :group 'org)
(defcustom zpm-port 23119 "Local Zotero HTTP server port." :type 'integer :group 'zpm)
(defcustom zpm-request-timeout 5 "Maximum seconds to wait for local Zotero." :type 'number :group 'zpm)

(define-error 'zpm-local-api-disabled "Zotero local API is disabled" 'user-error)

;;;###autoload
(defun zpm-picker-setup ()
  "Show the Zotero and Emacs settings needed for the paper picker."
  (interactive)
  (with-help-window "*ZPM Picker Setup*"
    (princ "Zotero paper picker setup\n\n")
    (princ "1. Open Zotero with ZPM installed (1.3.2 or newer for Zotero 10).\n")
    (princ "2. Open Zotero → Settings → Advanced.\n")
    (princ "3. Enable: Allow other applications on this computer to communicate with Zotero.\n")
    (princ "   This allows local applications to read your Zotero library. No online API key is needed.\n")
    (princ "4. Select a collection under My Library.\n")
    (princ "5. Return to your Org note and run M-x zpm-insert-paper-link again.\n\n")
    (princ "Emacs must load zpm-org-picker.el and the native zotero-item link handler.\n")
    (princ "No restart is needed after changing the Zotero permission. No setting is changed by this help.\n")
    (princ "Optional Emacs settings: M-x customize-variable → zpm-port (23119 by default),\n")
    (princ "or zpm-request-timeout (5 seconds). Vertico/Orderless are optional.\n")))

(defun zpm--request-with-setup (&optional collection)
  "Request COLLECTION and offer setup help if local access is disabled."
  (condition-case err
      (zpm--request collection)
    (zpm-local-api-disabled
     (when (y-or-n-p "Zotero local access is disabled. Show the steps to enable it? ")
       (zpm-picker-setup))
     (user-error "%s Retry the picker after enabling it" (error-message-string err)))))

(defun zpm--key (key)
  "Return validated Zotero KEY or signal a user error."
  (unless (and (stringp key) (let ((case-fold-search nil))
                              (string-match-p "\\`[23456789ABCDEFGHIJKLMNPQRSTUVWXYZ]\\{8\\}\\'" key)))
    (user-error "Invalid Zotero key; expected eight uppercase Zotero characters"))
  key)

(defun zpm--label (text)
  "Make TEXT safe for a single-line Org link label."
  (string-trim (replace-regexp-in-string
                "[[:space:][:cntrl:]]+" " "
                (replace-regexp-in-string "]" "］"
                                          (replace-regexp-in-string "\\[" "［" text t t) t t))))

(defun zpm--remembered-collection ()
  "Read the current Org note's file-wide ZPM_COLLECTION keyword."
  (save-restriction
    (widen)
    (let ((values (cdr (assoc "ZPM_COLLECTION" (org-collect-keywords '("ZPM_COLLECTION"))))))
      (when (> (length values) 1) (user-error "Keep only one #+ZPM_COLLECTION line in this note"))
      (when values (zpm--key (string-trim (car values)))))))

(defun zpm--request (&optional collection)
  "Read papers from COLLECTION, or the current Zotero collection."
  (when collection (zpm--key collection))
  (unless (and (integerp zpm-port) (< 0 zpm-port 65536)
               (numberp zpm-request-timeout) (> zpm-request-timeout 0))
    (user-error "Invalid local Zotero port or timeout"))
  (let* ((url-request-method "GET")
         (url-request-extra-headers '(("X-ZPM-Client" . "emacs") ("Accept" . "application/json")
                                      ("Zotero-Allowed-Request" . "true")))
         (url-proxy-services nil)
         (url-max-redirections 0)
         (url-show-status nil)
         (address (format "http://127.0.0.1:%d/zpm/papers%s" zpm-port
                          (if collection (concat "?collection=" collection) "")))
         (buffer (condition-case nil
                     (url-retrieve-synchronously address t t zpm-request-timeout)
                   (error nil))))
    (unless (buffer-live-p buffer)
      (user-error "Cannot reach Zotero. Open Zotero with ZPM (1.3.2 or newer for Zotero 10) and check the local API setting"))
    (unwind-protect
        (with-current-buffer buffer
          (goto-char (point-min))
          (unless (re-search-forward "\r?\n\r?\n" nil t) (user-error "Invalid response from Zotero"))
          (let* ((status url-http-response-status)
                 (json-object-type 'alist) (json-array-type 'list)
                 (json-key-type 'symbol) (json-false nil) (json-null nil)
                 (body (buffer-substring-no-properties (point) (point-max)))
                 ;; url-retrieve returns raw bytes; JSON strings are UTF-8.
                 (payload (condition-case nil
                              (json-read-from-string
                               (if enable-multibyte-characters body
                                 (decode-coding-string body 'utf-8)))
                            (error nil))))
            (when (and (equal status 403)
                       (or (equal (alist-get 'code payload) "local_api_disabled")
                           ;; Compatibility with the first picker preview.
                           (let ((message (alist-get 'error payload)))
                             (and (stringp message)
                                  (string-match-p "Allow other applications on this computer" message)))))
              (signal 'zpm-local-api-disabled (list (alist-get 'error payload))))
            (unless (equal status 200)
              (user-error "%s" (or (alist-get 'error payload)
                                    (if (equal status 404) "Install ZPM in Zotero (1.3.2 or newer for Zotero 10)"
                                      (format "Zotero returned HTTP %s" status)))))
            (unless (and (equal (alist-get 'schema payload) 1)
                         (listp (alist-get 'papers payload))
                         (assq 'papers payload)
                         (stringp (alist-get 'name (alist-get 'collection payload))))
              (user-error "Invalid picker data from Zotero"))
            (zpm--key (alist-get 'key (alist-get 'collection payload)))
            (when (and collection (not (equal collection (alist-get 'key (alist-get 'collection payload)))))
              (user-error "Zotero returned a different collection"))
            payload))
      (kill-buffer buffer))))

(defun zpm--choose-paper (payload)
  "Choose a paper in PAYLOAD with visible author, year, title, and key."
  (let ((papers (alist-get 'papers payload)) candidates seen)
    (unless papers (user-error "No paper records directly in this collection"))
    (dolist (paper papers)
      (unless (listp paper) (user-error "Invalid paper metadata from Zotero"))
      (let ((key (zpm--key (alist-get 'key paper))))
        (when (member key seen) (user-error "Duplicate paper key returned by Zotero"))
        (push key seen)
        (unless (cl-every (lambda (field) (stringp (alist-get field paper))) '(authors year title))
          (user-error "Invalid paper metadata from Zotero"))
        (push (cons (format "%s · %s · %s [%s]"
                            (zpm--label (alist-get 'authors paper))
                            (zpm--label (alist-get 'year paper))
                            (zpm--label (alist-get 'title paper)) key) paper) candidates)))
    (setq candidates (nreverse candidates))
    (let* ((completion-ignore-case t)
           (prompt (format "Paper in %s: " (zpm--label (alist-get 'name (alist-get 'collection payload)))))
           (choice (minibuffer-with-setup-hook
                       (lambda ()
                         (unless (or (bound-and-true-p vertico-mode) (bound-and-true-p ivy-mode)
                                     (bound-and-true-p icomplete-mode))
                           (minibuffer-completion-help)))
                     (completing-read prompt candidates nil t)))
           (paper (cdr (assoc choice candidates))))
      (unless paper (user-error "No paper selected"))
      paper)))

(defun zpm--pick ()
  "Return the selected paper and collection from the current Org note context."
  (unless (derived-mode-p 'org-mode) (user-error "Open an Org note first"))
  (let* ((payload (zpm--request-with-setup (zpm--remembered-collection)))
         (paper (zpm--choose-paper payload)))
    (list paper (zpm--key (alist-get 'key (alist-get 'collection payload))))))

;;;###autoload
(defun zpm-insert-paper-link ()
  "Choose a paper and insert its collection-specific Org link at point."
  (interactive)
  (barf-if-buffer-read-only)
  (pcase-let ((`(,paper ,collection) (zpm--pick)))
    (insert (format "[[zotero-item:%s?collection=%s][%s]]"
                    (zpm--key (alist-get 'key paper)) collection
                    (zpm--label (alist-get 'title paper))))))

;;;###autoload
(defun zpm-open-paper ()
  "Choose a paper and select its record in Zotero, without inserting text."
  (interactive)
  (unless (eq system-type 'darwin) (user-error "Opening Zotero records currently requires macOS"))
  (pcase-let ((`(,paper ,collection) (zpm--pick)))
    (start-process "zpm-paper" nil "/usr/bin/open"
                   (format "zotero://select/library/collections/%s/items/%s"
                           collection (zpm--key (alist-get 'key paper))))))

;;;###autoload
(defun zpm-remember-collection ()
  "Remember Zotero's current collection in this Org note; save the note to persist."
  (interactive)
  (unless (derived-mode-p 'org-mode) (user-error "Open an Org note first"))
  (barf-if-buffer-read-only)
  (let* ((payload (zpm--request-with-setup))
         (collection (alist-get 'collection payload))
         (key (zpm--key (alist-get 'key collection))))
    (zpm-forget-collection)
    (save-excursion
      (save-restriction
        (widen)
        (goto-char (point-min))
        (insert "#+ZPM_COLLECTION: " key "\n")))
    (message "Remembering %s; save this Org note to keep it" (alist-get 'name collection))))

;;;###autoload
(defun zpm-forget-collection ()
  "Remove this note's collection setting and follow Zotero's selection again."
  (interactive)
  (unless (derived-mode-p 'org-mode) (user-error "Open an Org note first"))
  (barf-if-buffer-read-only)
  (save-excursion
    (save-restriction
      (widen)
      (let (positions)
        (org-element-map (org-element-parse-buffer) 'keyword
          (lambda (keyword)
            (when (equal (org-element-property :key keyword) "ZPM_COLLECTION")
              (push (org-element-property :begin keyword) positions))))
        ;; Reverse document order keeps earlier positions valid and leaves
        ;; examples/source blocks (which are not keyword elements) untouched.
        (dolist (position positions)
          (goto-char position)
          (delete-region (line-beginning-position)
                         (min (point-max) (1+ (line-end-position))))))))
  (when (called-interactively-p 'interactive) (message "Following Zotero's selected collection; save the note to keep this change")))

(provide 'zpm-org-picker)
;;; zpm-org-picker.el ends here
