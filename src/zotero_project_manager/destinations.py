"""Desktop handoffs for freshly exported Zotero files."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import webbrowser
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

from .models import ExportStats

DESTINATIONS = ("gemini-notebook", "devonthink")
NOTEBOOK_URL = "https://notebook.google.com/"
RESOURCES = Path(__file__).with_name("resources")


class DestinationError(RuntimeError):
    """Raised when an export cannot be handed to a desktop application."""


def validate_destination(destination: str | None, notebook_url: str | None = None) -> None:
    """Validate routing before any export writes or applications are opened."""

    if destination is not None and destination not in DESTINATIONS:
        raise DestinationError(f"Unknown destination {destination!r}; choose {', '.join(DESTINATIONS)}.")
    if notebook_url:
        if destination != "gemini-notebook":
            raise DestinationError("--notebook-url requires --to gemini-notebook.")
        parsed = urlsplit(notebook_url)
        try:
            port = parsed.port
        except ValueError as exc:
            raise DestinationError("Invalid Gemini Notebook URL.") from exc
        if (
            parsed.scheme != "https"
            or parsed.hostname not in {"notebook.google.com", "notebooklm.google.com"}
            or parsed.username is not None
            or parsed.password is not None
            or port not in {None, 443}
        ):
            raise DestinationError("Use an HTTPS notebook.google.com or notebooklm.google.com URL.")


def delivery_plan(stats: ExportStats) -> dict[str, object]:
    """Include only this export's files, rejecting paths outside its workspace."""

    workspace = stats.workspace.resolve()
    files = []
    seen: set[Path] = set()
    for relative in stats.delivery_files:
        parts = relative.split("/")
        if not parts or PurePosixPath(relative).is_absolute() or any(
            part in {"", ".", "..", ".zpm"} or "\\" in part or ":" in part for part in parts
        ):
            raise DestinationError(f"Unsafe delivery path: {relative}")
        candidate = workspace.joinpath(*parts).resolve()
        if not candidate.is_relative_to(workspace) or not candidate.is_file():
            raise DestinationError(f"Exported file is missing or outside its workspace: {relative}")
        if candidate not in seen:
            files.append({"path": str(candidate), "relative": relative})
            seen.add(candidate)
    return {"workspace": str(workspace), "name": workspace.name, "files": files}


def run_desktop_script(script: str, plan: dict[str, object], group: str = "") -> str:
    """Run bundled AppleScript with data in a temporary JSON file, never as code."""

    if sys.platform != "darwin":
        raise DestinationError("DEVONthink integration requires macOS.")
    with tempfile.TemporaryDirectory(prefix="zpm-handoff-") as directory:
        plan_path = Path(directory) / "files.json"
        plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
        try:
            result = subprocess.run(
                ["/usr/bin/osascript", str(RESOURCES / script), str(plan_path), group],
                capture_output=True,
                text=True,
                timeout=600,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise DestinationError(
                "The app handoff timed out. Files remain exported; check DEVONthink before retrying."
            ) from exc
        except OSError as exc:
            raise DestinationError(f"Could not start the desktop handoff: {exc}") from exc
    if result.returncode:
        detail = result.stderr.strip()[:2000]
        app_name = "Finder" if script == "reveal-files.applescript" else "DEVONthink"
        raise DestinationError(
            f"Desktop handoff failed: {detail or 'osascript returned an error'}. "
            f"If macOS denied access, allow your terminal to control {app_name} in "
            "System Settings → Privacy & Security → Automation."
        )
    return result.stdout.strip()


def deliver(
    stats: ExportStats,
    destination: str,
    *,
    notebook_url: str | None = None,
    devonthink_group: str = "",
    prepare_only: bool = False,
) -> str:
    """Open prepared notebook sources or index exported files in DEVONthink."""

    validate_destination(destination, notebook_url)
    plan = delivery_plan(stats)
    count = len(plan["files"])
    if not count:
        return f"{stats.collection_name}: no available files to send."
    if prepare_only:
        return f"Prepared {count} files for {destination} in {stats.workspace}; no apps opened."
    if destination == "devonthink":
        return run_desktop_script("devonthink.applescript", plan, devonthink_group)

    opened = webbrowser.open(notebook_url or NOTEBOOK_URL)
    notice = "" if opened else f"Open {notebook_url or NOTEBOOK_URL} in your browser. "
    if sys.platform == "darwin":
        try:
            run_desktop_script("reveal-files.applescript", plan)
        except DestinationError:
            notice += f"Open {stats.workspace} in Finder to select the prepared files. "
    else:
        try:
            if sys.platform == "win32":
                import os
                os.startfile(stats.workspace)
            else:
                subprocess.run(["xdg-open", str(stats.workspace)], check=True, timeout=15)
        except (OSError, subprocess.SubprocessError):
            notice += f"Open {stats.workspace} in your file manager. "
    return (
        notice + f"{count} files ready. In Gemini Notebook, open or create a notebook, "
        "then drag the selected files into Add sources (or use Upload files). "
        "Nothing has been uploaded yet; check the Sources panel after uploading. "
        "Repeated uploads can create duplicate sources."
    )
