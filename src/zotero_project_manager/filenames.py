"""Portable and deterministic filename generation."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from .models import ZoteroAttachment

DEFAULT_FILENAME_TEMPLATE = "author_year_title"
FILENAME_TEMPLATES = (
    DEFAULT_FILENAME_TEMPLATE,
    "year_author_title",
    "title_author_year",
    "title_year_author",
    "year_title_author",
    "title",
)

_ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_SPACE = re.compile(r"\s+")
_YEAR = re.compile(r"(?<!\d)(\d{4})(?!\d)")
_RESERVED_WINDOWS_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def sanitize_component(value: str, *, fallback: str = "Untitled", max_length: int = 180) -> str:
    """Return a portable file or directory name component."""

    normalized = unicodedata.normalize("NFC", value)
    normalized = _ILLEGAL.sub("-", normalized)
    normalized = _SPACE.sub(" ", normalized).strip(" .")
    if not normalized:
        normalized = fallback
    if normalized.upper() in _RESERVED_WINDOWS_NAMES:
        normalized = f"_{normalized}"
    if len(normalized) > max_length:
        normalized = normalized[:max_length].rstrip(" .-")
    return normalized or fallback


def extract_year(date: str | None) -> str | None:
    """Extract the first standalone four-digit year from a Zotero date."""

    if not date:
        return None
    match = _YEAR.search(date)
    return match.group(1) if match else None


def validate_filename_template(template: str) -> str:
    """Return a supported filename template or raise ``ValueError``."""

    normalized = template.strip().casefold()
    if normalized not in FILENAME_TEMPLATES:
        choices = ", ".join(FILENAME_TEMPLATES)
        raise ValueError(f"Unknown filename template {template!r}; choose one of: {choices}")
    return normalized


def attachment_filename(
    attachment: ZoteroAttachment,
    template: str = DEFAULT_FILENAME_TEMPLATE,
) -> str:
    """Build a metadata filename using a validated named template."""

    source = attachment.source_path
    source_stem = source.stem if source else Path(attachment.original_path).stem
    extension = source.suffix if source and source.suffix else Path(attachment.original_path).suffix
    extension = extension.lower() or ".bin"

    title = attachment.title
    if title and extension != ".bin" and title.casefold().endswith(extension.casefold()):
        title = title[: -len(extension)].rstrip(" .")

    author = attachment.creators[0] if attachment.creators else None
    year = extract_year(attachment.date)
    resolved_title = title or source_stem or attachment.item_key or "Untitled"
    components = {
        "author": author,
        "year": year,
        "title": resolved_title,
    }
    order = validate_filename_template(template).split("_")
    parts = [components[field] for field in order if components[field]]
    stem = sanitize_component(" - ".join(part for part in parts if part))
    return f"{stem}{extension}"


def choose_available_name(
    desired: str,
    reserved: set[str],
    *,
    key: str | None = None,
) -> str:
    """Choose a collision-free filename and reserve it case-insensitively."""

    candidate = desired
    normalized = candidate.casefold()
    if normalized not in reserved:
        reserved.add(normalized)
        return candidate

    path = Path(desired)
    suffix = path.suffix
    stem = path.stem
    if key:
        candidate = f"{stem} [{sanitize_component(key, max_length=32)}]{suffix}"
        normalized = candidate.casefold()
        if normalized not in reserved:
            reserved.add(normalized)
            return candidate

    index = 2
    while True:
        candidate = f"{stem} ({index}){suffix}"
        normalized = candidate.casefold()
        if normalized not in reserved:
            reserved.add(normalized)
            return candidate
        index += 1
