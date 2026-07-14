#!/usr/bin/env python3
"""Build a reproducible Zotero companion-plugin XPI without extra dependencies."""

from __future__ import annotations

import hashlib
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
    "preferences.xhtml",
    "preferences.js",
    "preferences.css",
    "zpm.js",
    "locale/en-US/zpm.ftl",
)


def verify_update_feed(target: Path, version: str) -> None:
    """Verify that the update feed contains the exact XPI built for this version."""

    payload = json.loads((PLUGIN / "updates.json").read_text(encoding="utf-8"))
    updates = payload["addons"]["zpm@zotero-project-manager"]["updates"]
    update = next((item for item in updates if item.get("version") == version), None)
    if update is None:
        raise RuntimeError(f"updates.json has no entry for plugin version {version}")
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    expected_hash = f"sha256:{digest}"
    if update.get("update_hash") != expected_hash:
        raise RuntimeError(
            "updates.json hash does not match the built XPI: "
            f"expected {expected_hash}"
        )
    if not str(update.get("update_link", "")).endswith(f"/{target.name}"):
        raise RuntimeError(
            f"updates.json link does not reference the built XPI name: {target.name}"
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
    verify_update_feed(target, version)
    return target


if __name__ == "__main__":
    print(build())
