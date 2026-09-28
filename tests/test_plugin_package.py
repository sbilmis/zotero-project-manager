"""Keep the simplified installer free of removed desktop integrations."""

import importlib.util
import json
from pathlib import Path
from zipfile import ZipFile

import pytest


def test_preview_package_contains_core_plugin_and_settings_only(tmp_path, monkeypatch):
    script = Path(__file__).resolve().parents[1] / "scripts/build_zotero_plugin.py"
    spec = importlib.util.spec_from_file_location("zpm_plugin_builder", script)
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    monkeypatch.setattr(builder, "OUTPUT", tmp_path)
    with ZipFile(builder.build(development=True)) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == set(builder.FILES)
        assert not any(name.endswith(".applescript") for name in archive.namelist())
        assert "destinations.js" not in archive.namelist()
        assert b"destinations.js" not in archive.read("bootstrap.js")
        assert b'loadSubScript(rootURI + "links.js")' in archive.read("bootstrap.js")
        assert b"copyTextToClipboard" in archive.read("links.js")
        assert b'loadSubScript(rootURI + "picker.js")' in archive.read("bootstrap.js")
        assert b'"/zpm/papers"' in archive.read("picker.js")
        assert b"getScope('zpm-preferences').ZPMPreferences.init()" in archive.read("preferences.xhtml")
        compatibility = json.loads(archive.read("manifest.json"))["applications"]["zotero"]
        assert compatibility["strict_min_version"] == "9.0"
        assert compatibility["strict_max_version"] == "10.0.*"


@pytest.mark.parametrize("field", ["strict_min_version", "strict_max_version"])
def test_release_build_rejects_mismatched_update_compatibility(tmp_path, monkeypatch, field):
    script = Path(__file__).resolve().parents[1] / "scripts/build_zotero_plugin.py"
    spec = importlib.util.spec_from_file_location("zpm_plugin_builder", script)
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    monkeypatch.setattr(builder, "OUTPUT", tmp_path / "dist")
    target = builder.build(development=True)
    manifest = json.loads((builder.PLUGIN / "manifest.json").read_text())
    update = {"version": manifest["version"], "applications": {
        "zotero": dict(manifest["applications"]["zotero"]),
    }}
    update["applications"]["zotero"][field] = "8.0"
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    (tmp_path / "updates.json").write_text(json.dumps({"addons": {
        "zpm@zotero-project-manager": {"updates": [update]},
    }}))
    monkeypatch.setattr(builder, "PLUGIN", tmp_path)
    with pytest.raises(RuntimeError, match=field):
        builder.verify_update_feed(target, manifest["version"])
