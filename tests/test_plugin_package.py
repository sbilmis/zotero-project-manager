"""Keep the simplified installer free of removed desktop integrations."""

import importlib.util
from pathlib import Path
from zipfile import ZipFile


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
        assert b"getScope('zpm-preferences').ZPMPreferences.init()" in archive.read("preferences.xhtml")
