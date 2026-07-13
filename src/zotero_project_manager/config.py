"""TOML configuration and named project persistence."""

from __future__ import annotations

import json
import os
import re
import tempfile
import tomllib
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from .filenames import DEFAULT_FILENAME_TEMPLATE, validate_filename_template

_PROJECT_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


class ConfigError(ValueError):
    """Raised when a configuration file is invalid or cannot be updated."""


@dataclass(frozen=True, slots=True)
class ProjectConfig:
    """Reusable settings for one named Zotero export project."""

    name: str
    collections: tuple[str, ...]
    output_dir: Path | None = None
    recursive: bool = True
    include_non_pdf: bool = False
    prune: bool = False
    verify: bool = False
    metadata: bool = True
    annotations: bool = False
    filename_template: str = DEFAULT_FILENAME_TEMPLATE


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Global defaults and named projects loaded from one TOML file."""

    path: Path
    zotero_dir: Path | None = None
    output_dir: Path | None = None
    linked_attachment_base_dir: Path | None = None
    filename_template: str = DEFAULT_FILENAME_TEMPLATE
    projects: dict[str, ProjectConfig] = field(default_factory=dict)

    def with_project(self, project: ProjectConfig) -> "AppConfig":
        """Return a copy containing or replacing one named project."""

        projects = dict(self.projects)
        projects[project.name] = project
        return replace(self, projects=projects)


def default_config_path() -> Path:
    """Return the platform-neutral user configuration path."""

    override = os.environ.get("ZPM_CONFIG")
    if override:
        return Path(override).expanduser().resolve()
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return (base / "zpm" / "config.toml").expanduser().resolve()


def load_config(path: Path | None = None) -> AppConfig:
    """Load configuration, returning empty defaults when the file is absent."""

    config_path = (path or default_config_path()).expanduser().resolve()
    if not config_path.exists():
        return AppConfig(path=config_path)
    try:
        payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"Could not read configuration {config_path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ConfigError(f"Configuration root must be a table: {config_path}")

    projects_payload = payload.get("projects", {})
    if not isinstance(projects_payload, dict):
        raise ConfigError("'projects' must be a TOML table")
    projects: dict[str, ProjectConfig] = {}
    for name, values in projects_payload.items():
        if not isinstance(values, dict):
            raise ConfigError(f"Project {name!r} must be a TOML table")
        _validate_project_name(name)
        selectors = values.get("collections")
        if not isinstance(selectors, list) or not selectors or not all(
            isinstance(selector, str) and selector for selector in selectors
        ):
            raise ConfigError(f"Project {name!r} requires a non-empty string collection list")
        projects[name] = ProjectConfig(
            name=name,
            collections=tuple(selectors),
            output_dir=_optional_path(values.get("output_dir"), config_path),
            recursive=_boolean(values, "recursive", True, name),
            include_non_pdf=_boolean(values, "include_non_pdf", False, name),
            prune=_boolean(values, "prune", False, name),
            verify=_boolean(values, "verify", False, name),
            metadata=_boolean(values, "metadata", True, name),
            annotations=_boolean(values, "annotations", False, name),
            filename_template=_filename_template(
                values.get("filename_template", payload.get("filename_template")),
                context=f"Project {name!r}",
            ),
        )
    return AppConfig(
        path=config_path,
        zotero_dir=_optional_path(payload.get("zotero_dir"), config_path),
        output_dir=_optional_path(payload.get("output_dir"), config_path),
        linked_attachment_base_dir=_optional_path(
            payload.get("linked_attachment_base_dir"), config_path
        ),
        filename_template=_filename_template(
            payload.get("filename_template"), context="Global configuration"
        ),
        projects=projects,
    )


def save_config(config: AppConfig) -> None:
    """Atomically write known configuration fields as deterministic TOML."""

    lines = ["# Zotero Project Manager configuration"]
    for key, value in (
        ("zotero_dir", config.zotero_dir),
        ("output_dir", config.output_dir),
        ("linked_attachment_base_dir", config.linked_attachment_base_dir),
    ):
        if value is not None:
            lines.append(f"{key} = {_quote(str(value))}")
    lines.append(f"filename_template = {_quote(config.filename_template)}")
    for name in sorted(config.projects, key=str.casefold):
        project = config.projects[name]
        lines.extend(
            [
                "",
                f"[projects.{_quote(name)}]",
                f"collections = {_string_array(project.collections)}",
            ]
        )
        if project.output_dir is not None:
            lines.append(f"output_dir = {_quote(str(project.output_dir))}")
        lines.extend(
            [
                f"recursive = {str(project.recursive).lower()}",
                f"include_non_pdf = {str(project.include_non_pdf).lower()}",
                f"prune = {str(project.prune).lower()}",
                f"verify = {str(project.verify).lower()}",
                f"metadata = {str(project.metadata).lower()}",
                f"annotations = {str(project.annotations).lower()}",
                f"filename_template = {_quote(project.filename_template)}",
            ]
        )
    content = "\n".join(lines) + "\n"
    config.path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{config.path.name}.", dir=config.path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
        temporary_path.replace(config.path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def make_project(
    name: str,
    collections: list[str],
    *,
    output_dir: Path | None = None,
    recursive: bool = True,
    include_non_pdf: bool = False,
    prune: bool = False,
    verify: bool = False,
    metadata: bool = True,
    annotations: bool = False,
    filename_template: str = DEFAULT_FILENAME_TEMPLATE,
) -> ProjectConfig:
    """Validate and construct a named project."""

    _validate_project_name(name)
    if not collections or any(not selector for selector in collections):
        raise ConfigError("A named project requires at least one collection")
    try:
        validated_template = validate_filename_template(filename_template)
    except ValueError as exc:
        raise ConfigError(str(exc)) from exc
    return ProjectConfig(
        name=name,
        collections=tuple(collections),
        output_dir=output_dir.expanduser().resolve() if output_dir else None,
        recursive=recursive,
        include_non_pdf=include_non_pdf,
        prune=prune,
        verify=verify,
        metadata=metadata,
        annotations=annotations,
        filename_template=validated_template,
    )


def _validate_project_name(name: str) -> None:
    if not _PROJECT_NAME.fullmatch(name):
        raise ConfigError(
            "Project names must start with a letter or number and contain only "
            "letters, numbers, '.', '_', or '-'"
        )


def _optional_path(value: Any, config_path: Path) -> Path | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ConfigError("Configured paths must be non-empty strings")
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = config_path.parent / path
    return path.resolve()


def _boolean(values: dict[str, Any], key: str, default: bool, project: str) -> bool:
    value = values.get(key, default)
    if not isinstance(value, bool):
        raise ConfigError(f"Project {project!r} field {key!r} must be true or false")
    return value


def _filename_template(value: Any, *, context: str) -> str:
    if value is None:
        return DEFAULT_FILENAME_TEMPLATE
    if not isinstance(value, str) or not value:
        raise ConfigError(f"{context} filename_template must be a non-empty string")
    try:
        return validate_filename_template(value)
    except ValueError as exc:
        raise ConfigError(f"{context}: {exc}") from exc


def _quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _string_array(values: tuple[str, ...]) -> str:
    return "[" + ", ".join(_quote(value) for value in values) + "]"
