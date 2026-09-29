# Recording script: Zotero links for Markdown and Org

**Status: recording plan; no video has been recorded.**

Aim for a 75–90-second captioned screen recording. The companion text is the
[quick start](QUICKSTART.md), which remains usable without watching the video.

## Prepare the scene

- Use a demo collection named **Reading list** with a few public paper records
  and a PDF available locally. Prepare a Markdown note in Obsidian and an Org
  note named `demo.org`, both with the sentence `Related work: `.
- Install ZPM and complete the [Emacs setup](EMACS-SETUP.md) before recording.
  Set Zotero's **Open PDFs using** preference to **Zotero** for the PDF shot.
  Remove any remembered collection from the Org demo note.
- Show Zotero beside the note app used in each shot. Increase the text size so
  titles and commands are readable at the size used in the GitHub page.
- Show keystrokes and keep notifications and unrelated notes out of the frame.
  Select a real demo paper rather than typing illustrative Zotero keys.

## Shot list and captions

| Time | Screen action | Caption / optional narration |
| --- | --- | --- |
| 0–8 s | Show Zotero beside the Markdown note | “ZPM: Zotero links for Markdown and Org notes.” |
| 8–18 s | Right-click a demo paper → ZPM → Copy Link → Markdown | “Copy a Markdown link from Zotero.” |
| 18–30 s | Paste into Obsidian; click the link in Reading view | “Jump from your note back to the paper's record.” |
| 30–45 s | Copy the same paper as Org; paste into Emacs and press `C-c C-o` | “Choose Org for Emacs. Open the link with C-c C-o.” |
| 45–70 s | Select Reading list in Zotero. In Emacs, run `M-x zpm-insert-paper-link`, filter by author, and choose a result | “Emacs also has a paper picker: search and insert from your note.” |
| 70–82 s | Expand the paper, copy its PDF attachment as Markdown, paste and open it | “For a direct PDF link, select the PDF attachment.” |
| 82–90 s | End on the quick-start page | “Paper links select records. PDF links open PDFs. Choose the format for your notes.” |

Leave each pasted link and the picker results visible long enough to read.
Optional follow-up clips can cover page/annotation links or remembering a
collection in Emacs. Keep this first clip focused on the two note formats and
the distinction between paper and PDF links.

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
