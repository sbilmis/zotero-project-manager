# Recording script: Zotero links in Emacs

**Status: recording plan; no video has been recorded.**

Aim for a 75–90-second captioned screen recording. The companion text is the
[quick start](QUICKSTART.md), which remains usable without watching the video.

## Prepare the scene

- Use a demo collection named **Reading list** with a few public paper records.
  Use a fresh Org note named `demo.org` with the sentence `Related work: `.
- Complete the [setup](EMACS-SETUP.md) before recording. Do not include installation
  in this first video. Remove any remembered collection from the demo note.
- Arrange Zotero and Emacs side by side. Increase the text size so titles and
  commands are readable at the size used in the GitHub page.
- Show keystrokes and keep notifications and unrelated notes out of the frame.
  Select a real demo paper rather than typing illustrative Zotero keys.

## Shot list and captions

| Time | Screen action | Caption / optional narration |
| --- | --- | --- |
| 0–7 s | Show Zotero beside the Org note | “ZPM: link Zotero papers while writing in Emacs. One-time setup is linked below.” |
| 7–15 s | Select Reading list under My Library | “Choose a Zotero collection and leave Zotero open.” |
| 15–28 s | In Emacs, run `M-x zpm-insert-paper-link` | “Find a paper from your note.” |
| 28–40 s | Type part of an author or title; choose a result with Return | “Search, select, insert.” |
| 40–50 s | Put the cursor on the new link and press `C-c C-o` | “Open the link to select that paper's record in Zotero.” |
| 50–65 s | Run `M-x zpm-open-paper` and select another demo paper | “To open a record without inserting a link, use zpm-open-paper.” |
| 65–80 s | Run `M-x zpm-remember-collection`, then save the note | “Optional: remember this collection for this note. Save to keep it.” |
| 80–90 s | End on the quick-start page | “Paper links select records. PDF links open PDFs. See the quick start for both.” |

Leave the search results and inserted link visible long enough to read. An
optional second clip can cover copying PDF, page, and annotation links from
Zotero; keep this first clip focused on the paper picker.

## Put the finished video on GitHub

1. Export a captioned **H.264 MP4**. Aim for under **10 MB** to fit GitHub's free
   repository attachment limit. Keep an accessible text transcript with the clip.
2. Upload the finished MP4 as a repository issue or pull-request attachment.
   GitHub returns an attachment URL. Upload only the final demo recording.
3. Add a linked thumbnail labeled **Watch the 90-second walkthrough** near the
   top of the README and quick-start page. Use the uploaded video URL as the
   target, and check playback on GitHub in a browser.
4. Keep the quick-start instructions beside the video. Do not add an empty
   player, placeholder download link, or “Watch” button before the clip exists.

GitHub documents its supported video formats, attachment limits, and H.264
recommendation in [Attaching files](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/attaching-files).
The small screenshot lives in the repository; the video can use GitHub's
attachment hosting. A separate website or YouTube channel is optional.
