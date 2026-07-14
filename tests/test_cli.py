from typer.testing import CliRunner

from zotero_project_manager.cli import app
from zotero_project_manager.config import AppConfig, save_config


runner = CliRunner()


def test_list_command(zotero_fixture: object) -> None:
    fixture = zotero_fixture
    result = runner.invoke(app, ["list", "--database", str(fixture.database)])  # type: ignore[attr-defined]
    assert result.exit_code == 0, result.output
    assert "My-AI [ROOTKEY1]" in result.output
    assert "Books [BOOKKEY1]" in result.output


def test_multi_collection_export(tmp_path: object, zotero_fixture: object) -> None:
    fixture = zotero_fixture
    output = tmp_path / "out"  # type: ignore[operator]
    result = runner.invoke(
        app,
        [
            "export",
            "My-AI",
            "Claude",
            "--database",
            str(fixture.database),  # type: ignore[attr-defined]
            "--output",
            str(output),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (output / "My-AI" / "manifest.json").is_file()
    assert (output / "Claude" / "manifest.json").is_file()


def test_export_cli_supports_annotations_and_filename_template(
    tmp_path: object, zotero_fixture: object
) -> None:
    fixture = zotero_fixture
    output = tmp_path / "out"  # type: ignore[operator]
    result = runner.invoke(
        app,
        [
            "export",
            "My-AI",
            "--database",
            str(fixture.database),  # type: ignore[attr-defined]
            "--output",
            str(output),
            "--annotations",
            "--annotation-layout",
            "sidecar",
            "--filename-template",
            "year_author_title",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "2 annotation files" in result.output
    assert (
        output
        / "My-AI"
        / "Books"
        / "2021 - Chollet - Deep Learning with Python.annotations.md"
    ).is_file()


def test_status_reports_without_writing(tmp_path: object, zotero_fixture: object) -> None:
    fixture = zotero_fixture
    output = tmp_path / "out"  # type: ignore[operator]
    export_result = runner.invoke(
        app,
        ["export", "My-AI", "--database", str(fixture.database), "--output", str(output)],  # type: ignore[attr-defined]
    )
    assert export_result.exit_code == 0, export_result.output
    manifest = output / "My-AI" / "manifest.json"
    before = manifest.read_bytes()
    result = runner.invoke(
        app,
        ["status", "My-AI", "--database", str(fixture.database), "--output", str(output)],  # type: ignore[attr-defined]
    )
    assert result.exit_code == 0, result.output
    assert "2 unchanged" in result.output
    assert manifest.read_bytes() == before


def test_doctor_reports_read_only_database(tmp_path: object, zotero_fixture: object) -> None:
    fixture = zotero_fixture
    result = runner.invoke(
        app,
        [
            "doctor",
            "--database",
            str(fixture.database),  # type: ignore[attr-defined]
            "--output",
            str(tmp_path / "out"),  # type: ignore[operator]
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Read-only SQLite connection works" in result.output
    assert "[OK" in result.output


def test_config_set_and_show(tmp_path: object, zotero_fixture: object) -> None:
    fixture = zotero_fixture
    path = tmp_path / "config.toml"  # type: ignore[operator]
    output = tmp_path / "exports"  # type: ignore[operator]
    result = runner.invoke(
        app,
        [
            "--config",
            str(path),
            "config",
            "set",
            "--zotero-dir",
            str(fixture.data_dir),  # type: ignore[attr-defined]
            "--output",
            str(output),
            "--annotation-layout",
            "bundle",
        ],
    )
    assert result.exit_code == 0, result.output
    shown = runner.invoke(app, ["--config", str(path), "config", "show"])
    assert shown.exit_code == 0, shown.output
    assert str(output) in shown.output
    assert "Annotation layout: bundle" in shown.output
    assert "Named projects: 0" in shown.output


def test_named_project_sync_uses_saved_settings(tmp_path: object, zotero_fixture: object) -> None:
    fixture = zotero_fixture
    path = tmp_path / "config.toml"  # type: ignore[operator]
    output = tmp_path / "exports"  # type: ignore[operator]
    save_config(
        AppConfig(
            path=path,
            zotero_dir=fixture.data_dir,  # type: ignore[attr-defined]
            output_dir=output,
        )
    )
    added = runner.invoke(
        app,
        ["--config", str(path), "project", "add", "ai", "My-AI"],
    )
    assert added.exit_code == 0, added.output
    listed = runner.invoke(app, ["--config", str(path), "project", "list"])
    assert listed.exit_code == 0, listed.output
    assert "ai: My-AI" in listed.output

    preview = runner.invoke(app, ["--config", str(path), "sync", "ai", "--dry-run"])
    assert preview.exit_code == 0, preview.output
    assert "2 new" in preview.output
    assert not output.exists()

    synced = runner.invoke(app, ["--config", str(path), "sync", "ai"])
    assert synced.exit_code == 0, synced.output
    assert (output / "My-AI" / "manifest.json").is_file()


def test_direct_export_uses_configured_defaults(tmp_path: object, zotero_fixture: object) -> None:
    fixture = zotero_fixture
    path = tmp_path / "config.toml"  # type: ignore[operator]
    output = tmp_path / "exports"  # type: ignore[operator]
    save_config(
        AppConfig(
            path=path,
            zotero_dir=fixture.data_dir,  # type: ignore[attr-defined]
            output_dir=output,
        )
    )
    result = runner.invoke(app, ["--config", str(path), "export", "My-AI"])
    assert result.exit_code == 0, result.output
    assert (output / "My-AI" / "manifest.json").is_file()
