"""Destination contracts without changing personal libraries or opening apps."""

from __future__ import annotations

import json
import sqlite3
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest
from typer.testing import CliRunner

from zotero_project_manager import destinations
from zotero_project_manager.cli import app
from zotero_project_manager.collections import build_collection_forest, resolve_collection
from zotero_project_manager.exporter import CollectionExporter
from zotero_project_manager.models import ExportStats
from zotero_project_manager.zotero import ZoteroDatabase


def export_fixture(fixture, output: Path, **options) -> ExportStats:
    """Export the synthetic fixture through the same path used by the CLI."""
    with ZoteroDatabase(fixture.data_dir) as database:
        records = database.list_collections()
        return CollectionExporter(database, output, **options).export_many(
            [resolve_collection(records, "My-AI")], build_collection_forest(records)
        )[0]


def test_delivery_excludes_removed_missing_and_unmanaged_files(tmp_path, zotero_fixture):
    output = tmp_path / "out"
    first = export_fixture(zotero_fixture, output)
    (first.workspace / "personal.txt").write_text("not for delivery")
    zotero_fixture.first_pdf.unlink()
    with sqlite3.connect(zotero_fixture.database) as connection:
        connection.execute("DELETE FROM collectionItems WHERE itemID = 200")
    second = export_fixture(zotero_fixture, output)
    assert second.missing == 1 and second.removed == 1
    assert list(second.workspace.rglob("*.pdf"))  # Old copies are still on disk.
    assert destinations.delivery_plan(second)["files"] == []


def test_notebook_delivery_contains_current_notes_and_overview(tmp_path, zotero_fixture):
    stats = export_fixture(zotero_fixture, tmp_path / "out", export_profile="notebooklm")
    paths = [item["relative"] for item in destinations.delivery_plan(stats)["files"]]
    assert len(paths) == 5
    assert sum(path.endswith(".pdf") for path in paths) == 2
    assert sum(path.endswith(".annotations.md") for path in paths) == 2
    assert "collection-overview.md" in paths
    assert all("/" not in path for path in paths)


@pytest.mark.parametrize("relative", ["../secret.txt", "/tmp/secret", ".zpm/manifest.json", "a/../secret", "C:\\secret"])
def test_delivery_rejects_untrusted_paths(tmp_path, zotero_fixture, relative):
    stats = export_fixture(zotero_fixture, tmp_path / "out")
    with pytest.raises(destinations.DestinationError, match="Unsafe"):
        destinations.delivery_plan(replace(stats, delivery_files=(relative,)))


def test_delivery_rejects_symlink_escape(tmp_path, zotero_fixture):
    stats = export_fixture(zotero_fixture, tmp_path / "out")
    outside = tmp_path / "secret.txt"
    outside.write_text("private")
    target = stats.workspace / stats.delivery_files[0]
    target.unlink()
    try:
        target.symlink_to(outside)
    except OSError:
        pytest.skip("Symlinks are unavailable in this environment")
    with pytest.raises(destinations.DestinationError, match="outside"):
        destinations.delivery_plan(stats)


def test_script_receives_json_data_and_group_as_arguments(tmp_path, monkeypatch):
    plan = {"name": 'İnanç "quotes"', "files": [{"path": "/tmp/a 'quote'.pdf", "relative": "a.pdf"}]}
    calls = []

    def fake_run(argv, **options):
        calls.append(argv)
        assert json.loads(Path(argv[2]).read_text()) == plan
        assert argv[3] == "group-with-quotes\""
        assert options.get("shell") is None
        return subprocess.CompletedProcess(argv, 0, "Linked 1 files", "")

    monkeypatch.setattr(destinations.sys, "platform", "darwin")
    monkeypatch.setattr(destinations.subprocess, "run", fake_run)
    assert destinations.run_desktop_script("devonthink.applescript", plan, "group-with-quotes\"") == "Linked 1 files"
    assert not Path(calls[0][2]).exists()


def test_failed_app_handoff_is_reported(monkeypatch):
    monkeypatch.setattr(destinations.sys, "platform", "darwin")
    monkeypatch.setattr(destinations.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 1, "", "Access denied"))
    with pytest.raises(destinations.DestinationError, match="Access denied"):
        destinations.run_desktop_script("devonthink.applescript", {"files": []})


def test_devonthink_script_targets_only_version_four():
    source = (destinations.RESOURCES / "devonthink.applescript").read_text()
    assert 'tell application id "com.devon-technologies.think"' in source
    assert 'tell application id "DNtp"' not in source
    assert 'tell application id "com.devon-technologies.think3"' not in source
    guard = 'if (version as text) does not start with "4."'
    assert source.index(guard) < source.index("        activate")


def test_gemini_handoff_opens_requested_notebook_without_claiming_upload(tmp_path, zotero_fixture, monkeypatch):
    stats = export_fixture(zotero_fixture, tmp_path / "out", export_profile="notebooklm")
    opened = []
    selected = []
    monkeypatch.setattr(destinations.sys, "platform", "darwin")
    monkeypatch.setattr(destinations.webbrowser, "open", lambda url: opened.append(url) or True)
    monkeypatch.setattr(destinations, "run_desktop_script", lambda name, plan: selected.extend(plan["files"]))
    url = "https://notebooklm.google.com/notebook/example"
    message = destinations.deliver(stats, "gemini-notebook", notebook_url=url)
    assert opened == [url]
    assert len(selected) == 5
    assert "Nothing has been uploaded" in message


@pytest.mark.parametrize("url", ["http://notebook.google.com/", "https://notebook.google.com.evil.test/", "https://user@notebook.google.com/", "file:///tmp/test"])
def test_notebook_url_validation(url):
    with pytest.raises(destinations.DestinationError):
        destinations.validate_destination("gemini-notebook", url)


def test_cli_prepare_only_uses_notebook_profile_and_opens_nothing(tmp_path, zotero_fixture, monkeypatch):
    monkeypatch.setattr(destinations.webbrowser, "open", lambda *a: pytest.fail("Browser opened"))
    monkeypatch.setattr(destinations, "run_desktop_script", lambda *a: pytest.fail("App opened"))
    output = tmp_path / "out"
    result = CliRunner().invoke(app, [
        "export", "My-AI", "--database", str(zotero_fixture.database),
        "--output", str(output), "--to", "gemini-notebook", "--prepare-only",
    ])
    assert result.exit_code == 0, result.output
    assert (output / "My-AI - NotebookLM" / "collection-overview.md").is_file()
    assert "Prepared 5 files" in result.output
    assert "no apps opened" in result.output


def test_cli_dry_run_with_destination_writes_and_opens_nothing(tmp_path, zotero_fixture, monkeypatch):
    monkeypatch.setattr(destinations, "run_desktop_script", lambda *a: pytest.fail("App opened"))
    output = tmp_path / "out"
    result = CliRunner().invoke(app, [
        "export", "My-AI", "--database", str(zotero_fixture.database),
        "--output", str(output), "--to", "devonthink", "--dry-run",
    ])
    assert result.exit_code == 0, result.output
    assert not output.exists()
    assert "Would send to devonthink" in result.output


@pytest.mark.parametrize("options", [
    ["--to", "unknown"], ["--prepare-only"], ["--devonthink-group", "abc"],
    ["--to", "devonthink", "--notebook-url", "https://notebook.google.com/"],
])
def test_invalid_routing_fails_before_export(tmp_path, zotero_fixture, options):
    output = tmp_path / "out"
    result = CliRunner().invoke(app, [
        "export", "My-AI", "--database", str(zotero_fixture.database),
        "--output", str(output), *options,
    ])
    assert result.exit_code == 1
    assert not output.exists()
