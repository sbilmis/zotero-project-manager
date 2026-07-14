"""Shared test fixtures."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

import pytest


@dataclass(frozen=True)
class ZoteroFixture:
    data_dir: Path
    database: Path
    first_pdf: Path
    second_pdf: Path


@pytest.fixture()
def zotero_fixture(tmp_path: Path) -> ZoteroFixture:
    """Create a minimal Zotero-shaped database and attachment store."""

    data_dir = tmp_path / "Zotero"
    database = data_dir / "zotero.sqlite"
    data_dir.mkdir()
    connection = sqlite3.connect(database)
    connection.executescript(
        """
        CREATE TABLE collections (
            collectionID INTEGER PRIMARY KEY,
            collectionName TEXT NOT NULL,
            parentCollectionID INTEGER,
            libraryID INTEGER NOT NULL,
            key TEXT NOT NULL
        );
        CREATE TABLE items (
            itemID INTEGER PRIMARY KEY,
            libraryID INTEGER NOT NULL DEFAULT 1,
            key TEXT NOT NULL,
            dateAdded TEXT NOT NULL DEFAULT '2026-07-01 10:00:00',
            dateModified TEXT NOT NULL DEFAULT '2026-07-02 11:00:00'
        );
        CREATE TABLE collectionItems (
            collectionID INTEGER NOT NULL,
            itemID INTEGER NOT NULL
        );
        CREATE TABLE itemAttachments (
            itemID INTEGER PRIMARY KEY,
            parentItemID INTEGER,
            contentType TEXT,
            path TEXT
        );
        CREATE TABLE fields (
            fieldID INTEGER PRIMARY KEY,
            fieldName TEXT NOT NULL
        );
        CREATE TABLE itemDataValues (
            valueID INTEGER PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE itemData (
            itemID INTEGER NOT NULL,
            fieldID INTEGER NOT NULL,
            valueID INTEGER NOT NULL
        );
        CREATE TABLE creators (
            creatorID INTEGER PRIMARY KEY,
            firstName TEXT,
            lastName TEXT,
            fieldMode INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE itemCreators (
            itemID INTEGER NOT NULL,
            creatorID INTEGER NOT NULL,
            orderIndex INTEGER NOT NULL
        );
        CREATE TABLE tags (
            tagID INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );
        CREATE TABLE itemTags (
            itemID INTEGER NOT NULL,
            tagID INTEGER NOT NULL,
            type INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE itemAnnotations (
            itemID INTEGER PRIMARY KEY,
            parentItemID INTEGER NOT NULL,
            type INTEGER NOT NULL,
            authorName TEXT,
            text TEXT,
            comment TEXT,
            color TEXT,
            pageLabel TEXT,
            sortIndex TEXT NOT NULL,
            position TEXT NOT NULL,
            isExternal INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE itemNotes (
            itemID INTEGER PRIMARY KEY,
            parentItemID INTEGER,
            note TEXT,
            title TEXT
        );
        CREATE TABLE libraries (
            libraryID INTEGER PRIMARY KEY,
            type TEXT NOT NULL
        );
        CREATE TABLE groups (
            groupID INTEGER PRIMARY KEY,
            libraryID INTEGER NOT NULL UNIQUE
        );
        """
    )
    connection.executemany(
        "INSERT INTO collections VALUES (?, ?, ?, ?, ?)",
        [
            (1, "My-AI", None, 1, "ROOTKEY1"),
            (2, "Books", 1, 1, "BOOKKEY1"),
            (3, "Claude", None, 1, "CLAUDE01"),
        ],
    )
    connection.executemany(
        "INSERT INTO items (itemID, key) VALUES (?, ?)",
        [
            (100, "ITEM0001"),
            (101, "ATTACH01"),
            (102, "ANNOT001"),
            (103, "NOTE0001"),
            (200, "ITEM0002"),
            (201, "ATTACH02"),
        ],
    )
    connection.execute("INSERT INTO libraries VALUES (?, ?)", (1, "user"))
    connection.executemany(
        "INSERT INTO collectionItems VALUES (?, ?)",
        [(2, 100), (1, 200)],
    )
    connection.executemany(
        "INSERT INTO itemAttachments VALUES (?, ?, ?, ?)",
        [
            (101, 100, "application/pdf", "storage:deep-learning.pdf"),
            (201, 200, "application/pdf", "storage:attention.pdf"),
        ],
    )
    connection.executemany(
        "INSERT INTO fields VALUES (?, ?)",
        [(1, "title"), (2, "date"), (3, "DOI")],
    )
    connection.executemany(
        "INSERT INTO itemDataValues VALUES (?, ?)",
        [
            (1, "Deep Learning with Python"),
            (2, "2021"),
            (3, "Attention Is All You Need"),
            (4, "2017-06-12"),
            (5, "10.5555/attention"),
        ],
    )
    connection.executemany(
        "INSERT INTO itemData VALUES (?, ?, ?)",
        [(100, 1, 1), (100, 2, 2), (200, 1, 3), (200, 2, 4), (200, 3, 5)],
    )
    connection.executemany(
        "INSERT INTO creators VALUES (?, ?, ?, ?)",
        [(1, "François", "Chollet", 0), (2, "Ashish", "Vaswani", 0)],
    )
    connection.executemany(
        "INSERT INTO itemCreators VALUES (?, ?, ?)",
        [(100, 1, 0), (200, 2, 0)],
    )
    connection.executemany(
        "INSERT INTO tags VALUES (?, ?)",
        [(1, "AI"), (2, "Book"), (3, "Important"), (4, "Research note")],
    )
    connection.executemany(
        "INSERT INTO itemTags VALUES (?, ?, ?)",
        [(100, 2, 0), (102, 3, 0), (103, 4, 0), (200, 1, 0)],
    )
    connection.execute(
        "INSERT INTO itemAnnotations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            102,
            101,
            1,
            "Selcuk",
            "Neural networks learn useful representations.",
            "Connect this to the current model.",
            "#ffd400",
            "4",
            "00003|000001|00000",
            '{"pageIndex": 3, "rects": [[1, 2, 3, 4]]}',
            0,
        ),
    )
    connection.execute(
        "INSERT INTO itemNotes VALUES (?, ?, ?, ?)",
        (
            103,
            100,
            "<div><p><strong>Key idea</strong> for the project.</p><ul><li>Compare models</li></ul></div>",
            "Reading notes",
        ),
    )
    connection.commit()
    connection.close()

    first_pdf = data_dir / "storage" / "ATTACH01" / "deep-learning.pdf"
    second_pdf = data_dir / "storage" / "ATTACH02" / "attention.pdf"
    first_pdf.parent.mkdir(parents=True)
    second_pdf.parent.mkdir(parents=True)
    first_pdf.write_bytes(b"first-pdf")
    second_pdf.write_bytes(b"second-pdf")
    return ZoteroFixture(data_dir, database, first_pdf, second_pdf)
