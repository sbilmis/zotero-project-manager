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
