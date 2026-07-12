from typer.testing import CliRunner

from zotero_project_manager.cli import app


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
