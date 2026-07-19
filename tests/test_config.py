from pathlib import Path

import pytest

from zotero_project_manager.config import (
    AppConfig,
    ConfigError,
    load_config,
    make_project,
    save_config,
)


def test_config_round_trip_with_named_project(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    project = make_project(
        "ai",
        ["My-AI", "CLAUDE01"],
        output_dir=tmp_path / "projects",
        prune=True,
        verify=True,
        annotations=True,
        annotation_layout="bundle",
        filename_template="year_author_title",
        export_profile="notebooklm",
    )
    expected = AppConfig(
        path=path,
        zotero_dir=tmp_path / "Zotero",
        output_dir=tmp_path / "exports",
        linked_attachment_base_dir=tmp_path / "linked",
        annotation_layout="sidecar",
        filename_template="title_author_year",
        projects={"ai": project},
    )
    save_config(expected)
    assert load_config(path) == expected
    assert load_config(path).projects["ai"].metadata is True
    assert load_config(path).projects["ai"].annotations is True
    assert load_config(path).projects["ai"].annotation_layout == "sidecar"
    assert load_config(path).annotation_layout == "sidecar"
    assert load_config(path).projects["ai"].filename_template == "year_author_title"
    assert load_config(path).projects["ai"].export_profile == "notebooklm"


def test_relative_config_paths_resolve_from_config_directory(tmp_path: Path) -> None:
    path = tmp_path / "settings" / "config.toml"
    path.parent.mkdir()
    path.write_text(
        'output_dir = "../exports"\n\n[projects."ai"]\ncollections = ["My-AI"]\n',
        encoding="utf-8",
    )
    config = load_config(path)
    assert config.output_dir == (tmp_path / "exports").resolve()
    assert config.projects["ai"].collections == ("My-AI",)


def test_invalid_project_name_is_rejected() -> None:
    with pytest.raises(ConfigError, match="Project names"):
        make_project("not a project", ["My-AI"])


def test_invalid_filename_template_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown filename template"):
        make_project("ai", ["My-AI"], filename_template="random")


def test_invalid_annotation_layout_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown annotation layout"):
        make_project("ai", ["My-AI"], annotation_layout="random")


def test_invalid_export_profile_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown export profile"):
        make_project("ai", ["My-AI"], export_profile="random")


def test_missing_config_returns_empty_defaults(tmp_path: Path) -> None:
    path = tmp_path / "missing.toml"
    assert load_config(path) == AppConfig(path=path)
