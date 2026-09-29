#!/usr/bin/env python3
"""Gate PyPI publishing by the independently versioned release components."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tomllib


ROOT = Path(__file__).resolve().parents[1]


def publish_cli(tag: str, cli_version: str, plugin_version: str) -> bool:
    """Only a tag matching the CLI version may publish the Python package."""
    if tag == f"v{cli_version}":
        return True
    if tag == f"v{plugin_version}":
        return False
    raise ValueError("Release tag must match the CLI or plugin version; dispatch on a version tag.")


def main() -> None:
    cli_version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    plugin_version = json.loads((ROOT / "zotero-plugin/manifest.json").read_text())["version"]
    enabled = publish_cli(os.environ["ZPM_RELEASE_TAG"], cli_version, plugin_version)
    value = str(enabled).lower()
    print(f"publish_cli={value} (CLI {cli_version}, plugin {plugin_version})")
    with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as output:
        output.write(f"publish_cli={value}\n")


if __name__ == "__main__":
    main()
