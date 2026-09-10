"""Opt-in macOS smoke tests using DEVONthink 4 and synthetic text."""

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

from zotero_project_manager.destinations import run_desktop_script

pytestmark = pytest.mark.skipif(
    sys.platform != "darwin" or os.environ.get("ZPM_TEST_DESKTOP") != "1",
    reason="Set ZPM_TEST_DESKTOP=1 to test the installed macOS app in an isolated database.",
)


def applescript(source: str, *arguments: str) -> str:
    """Run a short test harness, with all variable values passed as arguments."""
    return subprocess.run(
        ["/usr/bin/osascript", "-e", source, *arguments],
        check=True, capture_output=True, text=True, timeout=60,
    ).stdout.strip()


@pytest.fixture
def permanent_test_directory():
    """DEVONthink deliberately imports files in the OS temp directory instead of indexing."""
    with tempfile.TemporaryDirectory(
        prefix=".zpm-desktop-test-", dir=Path(__file__).resolve().parents[1]
    ) as directory:
        yield Path(directory)


def test_devonthink4_indexes_once_and_refreshes_existing_file(permanent_test_directory: Path):
    tmp_path = permanent_test_directory
    database_path = tmp_path / "ZPM isolated smoke test.dtBase2"
    group_id = applescript("""
on run argv
    tell application id "com.devon-technologies.think"
        if (version as text) does not start with "4." then error "The smoke test requires DEVONthink 4."
        set testDatabase to create database (item 1 of argv)
        if testDatabase is missing value then error "Could not create the test database."
        return uuid of root of testDatabase
    end tell
end run
""", str(database_path))
    try:
        workspace = tmp_path / 'İnanç "research"'
        source = workspace / "Books" / "Paper.txt"
        source.parent.mkdir(parents=True)
        source.write_text("ZPM synthetic first version")
        plan = {
            "workspace": str(workspace), "name": workspace.name,
            "files": [{"path": str(source), "relative": "Books/Paper.txt"}],
        }
        first = run_desktop_script("devonthink.applescript", plan, group_id)
        assert "Linked 1 files" in first
        assert "DEVONthink 4" in first
        replacement = source.with_suffix(".new")
        replacement.write_text("ZPM synthetic updated version")
        replacement.replace(source)  # Match zpm's atomic export update.
        second = run_desktop_script("devonthink.applescript", plan, group_id)
        assert "Linked 0 files" in second
        assert "1 already present" in second
        result = applescript("""
on run argv
    tell application id "com.devon-technologies.think"
        set targetGroup to get record with uuid (item 1 of argv)
        set recordsFound to lookup records with path (item 2 of argv) in (database of targetGroup)
        return ((count of recordsFound) as text) & "|" & (plain text of item 1 of recordsFound)
    end tell
end run
""", group_id, str(source))
        assert result == "1|ZPM synthetic updated version"
    finally:
        applescript("""
on run argv
    tell application id "com.devon-technologies.think"
        set targetGroup to get record with uuid (item 1 of argv)
        close (database of targetGroup)
    end tell
end run
""", group_id)


def test_finder_selects_exact_sources(tmp_path: Path):
    files = [tmp_path / "First paper.txt", tmp_path / 'İnanç "second".txt']
    for file in files:
        file.write_text("Synthetic Finder selection test")
    unrelated = tmp_path / "Do not select.txt"
    unrelated.write_text("Not in the handoff")
    plan = {
        "workspace": str(tmp_path), "name": tmp_path.name,
        "files": [{"path": str(file), "relative": file.name} for file in files],
    }
    result = run_desktop_script("reveal-files.applescript", plan)
    assert "selected in Finder" in result
    expected = {str(file.resolve()) for file in files}
    try:
        for _ in range(30):
            selected = applescript("""
tell application "Finder"
    set selectedPaths to {}
    set selectedFiles to selection as alias list
    repeat with selectedItem in selectedFiles
        set end of selectedPaths to POSIX path of (selectedItem as alias)
    end repeat
end tell
set AppleScript's text item delimiters to linefeed
return selectedPaths as text
""")
            if set(selected.splitlines()) == expected:
                break
            time.sleep(0.1)
        assert set(selected.splitlines()) == expected
    finally:
        applescript("""
on run argv
    tell application "Finder"
        repeat with currentWindow in Finder windows
            try
                if POSIX path of (target of currentWindow as alias) is ((item 1 of argv) & "/") then close currentWindow
            end try
        end repeat
    end tell
end run
""", str(tmp_path))
