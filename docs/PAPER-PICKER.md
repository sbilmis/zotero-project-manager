# Emacs paper picker reference

**New to ZPM? Start with the [quick start](QUICKSTART.md).**
For installation and connection problems, use the [one-time setup](EMACS-SETUP.md).

The picker searches papers in a Zotero collection from an Org note. It uses the
collection selected in Zotero, or a collection remembered in that note.

## Insert a paper link

1. Select one collection under **My Library** in Zotero and leave Zotero running.
2. In an Org note, place the cursor where the link belongs and run
   **M-x zpm-insert-paper-link**.
3. Search by author, year, or title and press **Return** to choose a paper.
   Use your completion interface to browse; **C-g** cancels without inserting text.
4. Save your note. To open the link, put the cursor on it and press **C-c C-o**
   (`org-open-at-point`).

The inserted link remembers both the paper and its collection:

```org
Related work: [[zotero-item:ABCD2345?collection=6RIU3F76][Paper title]].
```

These keys are illustrative; the picker supplies the real ones. Opening the link
selects the paper's record in that collection. To open a PDF directly, copy a
[PDF link from Zotero](LINKS.md#copy-one-collection-paper-or-pdf).

The list is fetched each time and includes papers directly in the collection.
Subcollections are not expanded. Notes, attachments, and deleted entries are
omitted; regular bibliographic records of all types are included. Duplicate
titles remain separate results, distinguished by their Zotero keys.

## Open a paper without inserting text

Run **M-x zpm-open-paper** in your Org note and choose a paper from the same list.
Zotero selects that paper's record and the note stays unchanged. Opening records
with this command currently requires **macOS**.

## Remember a collection for a note

1. Select the desired collection in Zotero.
2. In your Org note, run **M-x zpm-remember-collection**.
3. Save the note.

The command adds a file-wide Org setting:

```org
#+ZPM_COLLECTION: 6RIU3F76
```

Both picker commands now use that collection, even if Zotero is showing another
one. Each note can remember its own collection. Renaming the collection does not
break the setting because it stores the collection's key. The setting also works
when the Org buffer is narrowed to a heading.

Run **zpm-remember-collection** again to replace it with Zotero's current
collection. Run **zpm-forget-collection** to return to following Zotero's
selection. Save after either change; the commands do not save automatically.
Existing links and keyword examples inside source/example blocks are preserved.

## Commands at a glance

| Command | Result |
| --- | --- |
| `zpm-insert-paper-link` | Insert the chosen paper's collection-specific Org link |
| `zpm-open-paper` | Select the chosen record in Zotero, without editing the note |
| `zpm-remember-collection` | Store Zotero's current collection in this note |
| `zpm-forget-collection` | Remove this note's collection setting |
| `zpm-picker-setup` | Show setup help in Emacs |

## Collection rules and troubleshooting

- **Supported selection:** exactly one personal-library collection. My Library
  itself, saved searches, group libraries, and multiple selected collections are
  unsupported. A remembered collection takes precedence over Zotero's selection.
- **Missing paper:** select its own subcollection; the picker does not search
  descendants. If the note remembers another collection, replace or forget that
  setting first.
- **Missing remembered collection:** replace or forget the setting. The picker
  reports the error instead of silently choosing a different collection.
- **Invalid or duplicate `ZPM_COLLECTION`:** keep one valid setting, or run
  `zpm-forget-collection` and remember the collection again.
- **Old collection-specific link no longer opens:** the paper may have been
  removed from that collection. For a link independent of collection membership,
  use ordinary **ZPM → Copy Link** in Zotero.
- **Connection or permission error:** follow the [setup troubleshooting](EMACS-SETUP.md#if-something-does-not-work).
  `zpm-picker-setup` also shows the local-access setting inside Emacs.

No completion package is required. Vertico can show candidates as a list and
Orderless can match words in any order. The default request timeout is five
seconds; optional settings are covered in the [setup guide](EMACS-SETUP.md).

The picker reads library metadata locally. It does not export PDFs, edit Zotero,
create citations or bibliographies, or upload library data. Developer checks and
manual acceptance steps are in [TESTING.md](TESTING.md#links-and-emacs-picker-checks).
