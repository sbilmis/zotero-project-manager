from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from zotero_project_manager.cli import app
from zotero_project_manager.diagnostics import run_diagnostics


runner = CliRunner()


def test_diagnostics_report_inventory_and_stable_codes(
    tmp_path: Path, zotero_fixture: object
) -> None:
    fixture = zotero_fixture
    results = run_diagnostics(
        zotero_data_dir=fixture.data_dir,  # type: ignore[attr-defined]
        database_path=fixture.database,  # type: ignore[attr-defined]
        output_root=tmp_path / "exports",
        detect_runtime=False,
    )
    by_code = {result.code: result for result in results}
    assert by_code["sqlite.read_only"].level == "ok"
    assert "3 collections" in by_code["sqlite.read_only"].message
    assert by_code["zotero.attachments"].level == "ok"
    assert "2 available" in by_code["zotero.attachments"].message
    assert by_code["zpm.output"].level == "ok"


def test_doctor_json_is_machine_readable(tmp_path: Path, zotero_fixture: object) -> None:
    fixture = zotero_fixture
    result = runner.invoke(
        app,
        [
            "doctor",
            "--database",
            str(fixture.database),  # type: ignore[attr-defined]
            "--output",
            str(tmp_path / "exports"),
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert {entry["code"] for entry in payload} >= {
        "zpm.runtime",
        "zotero.database",
        "sqlite.read_only",
        "zotero.attachments",
        "zpm.output",
    }


def test_output_inside_zotero_is_rejected(zotero_fixture: object) -> None:
    fixture = zotero_fixture
    results = run_diagnostics(
        zotero_data_dir=fixture.data_dir,  # type: ignore[attr-defined]
        database_path=fixture.database,  # type: ignore[attr-defined]
        output_root=fixture.data_dir / "Exports",  # type: ignore[attr-defined]
        detect_runtime=False,
    )
    output = next(result for result in results if result.code == "zpm.output")
    assert output.level == "error"
