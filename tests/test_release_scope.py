"""Prevent plugin-only releases from republishing an unchanged Python CLI."""

import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/release_scope.py"
spec = importlib.util.spec_from_file_location("release_scope", SCRIPT)
scope = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scope)


@pytest.mark.parametrize("tag,cli,plugin,expected", [
    ("v1.4.0", "1.3.2", "1.4.0", False),
    ("v1.3.2", "1.3.2", "1.3.2", True),
    ("v1.5.0", "1.5.0", "1.4.0", True),
])
def test_component_selection(tag, cli, plugin, expected):
    assert scope.publish_cli(tag, cli, plugin) is expected


@pytest.mark.parametrize("tag", ["main", "v9.9.9", "1.4.0", "v1.4.0\npublish_cli=true"])
def test_unknown_or_malformed_tags_fail_closed(tag):
    with pytest.raises(ValueError, match="Release tag"):
        scope.publish_cli(tag, "1.3.2", "1.4.0")


def test_workflow_entry_point_outputs_plugin_only_decision(tmp_path):
    script = tmp_path / "scripts" / SCRIPT.name
    script.parent.mkdir()
    shutil.copyfile(SCRIPT, script)
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "1.3.2"\n')
    plugin = tmp_path / "zotero-plugin"
    plugin.mkdir()
    (plugin / "manifest.json").write_text('{"version": "1.4.0"}')
    output = tmp_path / "outputs"
    result = subprocess.run(
        [sys.executable, str(script)],
        env={**os.environ, "ZPM_RELEASE_TAG": "v1.4.0", "GITHUB_OUTPUT": str(output)},
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert output.read_text() == "publish_cli=false\n"
