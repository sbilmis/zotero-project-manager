;;; org-links.test.el --- Test dispatch without opening applications -*- lexical-binding: t; -*-
(require 'ert)
(require 'cl-lib)
(defvar zpm-test-link-forms
  (with-temp-buffer
    (insert-file-contents (or (getenv "ZPM_ORG_CONFIG") "docs/emacs/zpm-org-links.el"))
    (goto-char (point-min))
    (search-forward "(defun sb/org-zotero-key")
    (goto-char (match-beginning 0))
    (cl-loop repeat 5 collect (read (current-buffer)))))
;; Test the deferred registration before loading Org, as at startup.
(dolist (form zpm-test-link-forms) (eval form t))
(require 'org)

(ert-deftest zpm-deferred-registration ()
  (should (eq (org-link-get-parameter "zotero-collection" :follow) #'sb/org-open-zotero-collection))
  (should (eq (org-link-get-parameter "zotero-item" :follow) #'sb/org-open-zotero-item))
  (should (eq (org-link-get-parameter "zotero-pdf" :follow) #'sb/org-open-zotero-pdf)))

(ert-deftest zpm-preserves-existing-zotero-registration ()
  (let ((org-link-parameters (copy-tree org-link-parameters)))
    (org-link-set-parameters "zotero" :follow #'ignore)
    (dolist (form zpm-test-link-forms) (eval form t))
    (should (eq (org-link-get-parameter "zotero" :follow) #'ignore))))

(ert-deftest zpm-org-activation-process-arguments ()
  (dolist (case '(("collection" "6RIU3F76" "select/library/collections/")
                  ("item" "ABCD2345" "select/library/items/")
                  ("pdf" "EFGH6789" "open-pdf/library/items/")
                  ("pdf" "EFGH6789?page=1" "open-pdf/library/items/")
                  ("pdf" "EFGH6789?page=5&annotation=JKLM2345" "open-pdf/library/items/")))
    (pcase-let ((`(,kind ,key ,prefix) case))
      (let (calls)
        (cl-letf (((symbol-function 'start-process) (lambda (&rest args) (push args calls)))
                  ((symbol-function 'shell-command) (lambda (&rest _) (ert-fail "Shell launched"))))
          (with-temp-buffer
            (org-mode)
            (insert (format "Read [[zotero-%s:%s][Label ［brackets］ 文献]] next." kind key))
            (goto-char (point-min))
            (search-forward "Label")
            (org-open-at-point)))
        (should (equal calls (list (list (concat "zotero-" kind) nil "/usr/bin/open"
                                         (concat "zotero://" prefix key)))))))))

(ert-deftest zpm-invalid-keys-never-launch-processes ()
  (cl-letf (((symbol-function 'start-process) (lambda (&rest _) (ert-fail "Invalid link launched process"))))
    (dolist (key '(nil "" "nil" "abcd2345" "ABCD1234" "ABCD0EFG" "ABCDOEFG" "ABCD2345\n" " ABCD2345" "ABCD2345;open"))
      (should-error (sb/org-open-zotero-collection key nil) :type 'user-error)
      (should-error (sb/org-open-zotero-item key nil) :type 'user-error)
      (should-error (sb/org-open-zotero-pdf key nil) :type 'user-error))
    (dolist (path '("EFGH6789?page=0" "EFGH6789?page=-1" "EFGH6789?page=1.5" "EFGH6789?page=01"
                    "EFGH6789?annotation=JKLM2345" "EFGH6789?page=2&annotation=nil"
                    "EFGH6789?page=2&annotation=jklm2345" "EFGH6789?page=2&x=3"
                    "EFGH6789?page=2\n" "EFGH6789%3Fpage=2" "EFGH6789?page=2&page=3"))
      (should-error (sb/org-open-zotero-pdf path nil) :type 'user-error))))

(ert-deftest zpm-collection-aware-item-activation ()
  (let (calls)
    (cl-letf (((symbol-function 'start-process) (lambda (&rest args) (push args calls))))
      (with-temp-buffer
        (org-mode)
        (insert "Read [[zotero-item:ABCD2345?collection=6RIU3F76][this paper]] next.")
        (goto-char 20)
        (org-open-at-point)))
    (should (equal calls '(("zotero-item" nil "/usr/bin/open"
                           "zotero://select/library/collections/6RIU3F76/items/ABCD2345"))))))

(ert-deftest zpm-invalid-collection-context-never-launches ()
  (cl-letf (((symbol-function 'start-process) (lambda (&rest _) (ert-fail "Invalid scoped link launched"))))
    (dolist (path '("ABCD2345?collection=" "ABCD2345?collection=nil"
                    "ABCD2345?collection=6riu3f76" "ABCD2345?collection=6RIU3F76&x=1"
                    "ABCD2345?collection=6RIU3F76\n" "ABCD2345/6RIU3F76"
                    "ABCD2345?collection=6RIU3F76?collection=6RIU3F76"))
      (should-error (sb/org-open-zotero-item path nil) :type 'user-error))))

(ert-run-tests-batch-and-exit)
