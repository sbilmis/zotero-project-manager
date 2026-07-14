#!/usr/bin/env python3
"""Build a reproducible Zotero companion-plugin XPI without extra dependencies."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "zotero-plugin"
OUTPUT = ROOT / "dist"
FILES = (
    "bootstrap.js",
    "manifest.json",
    "prefs.js",
    "zpm.js",
    "locale/en-US/zpm.ftl",
)


def build() -> Path:
    """Build the XPI and return its path."""

    manifest = json.loads((PLUGIN / "manifest.json").read_text(encoding="utf-8"))
    version = manifest["version"]
    target = OUTPUT / f"zpm-zotero-{version}.xpi"
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for relative in FILES:
            source = PLUGIN / relative
            info = zipfile.ZipInfo(relative, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, source.read_bytes())
    return target


if __name__ == "__main__":
    print(build())
