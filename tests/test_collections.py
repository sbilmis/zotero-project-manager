from pathlib import Path

import pytest

from zotero_project_manager.collections import (
    AmbiguousCollectionError,
    CollectionHierarchyError,
    build_collection_forest,
    collection_paths,
    format_collection_forest,
    resolve_collection,
)
from zotero_project_manager.models import Collection


def records() -> list[Collection]:
    return [
        Collection(1, "ROOT", "AI", None, 1),
        Collection(2, "BOOKS", "Books", 1, 1),
        Collection(3, "PAPERS", "Papers", 1, 1),
        Collection(4, "DEEP", "Deep", 2, 1),
    ]


def test_hierarchy_and_recursive_paths() -> None:
    forest = build_collection_forest(records())
    paths = collection_paths(forest[0])
    assert str(paths[1]) == "."
    assert str(paths[2]) == "Books"
    assert paths[4] == Path("Books") / "Deep"


def test_non_recursive_paths_only_include_root() -> None:
    forest = build_collection_forest(records())
    assert collection_paths(forest[0], recursive=False) == {1: Path()}


def test_collection_tree_output_includes_keys() -> None:
    output = format_collection_forest(build_collection_forest(records()))
    assert "My Library" in output
    assert "    AI [ROOT]" in output
    assert "        Books [BOOKS]" in output


def test_resolve_by_key_or_case_insensitive_name() -> None:
    assert resolve_collection(records(), "BOOKS").id == 2
    assert resolve_collection(records(), "papers").id == 3


def test_ambiguous_name_requires_key() -> None:
    duplicate = Collection(5, "OTHER", "AI", None, 1)
    with pytest.raises(AmbiguousCollectionError):
        resolve_collection([*records(), duplicate], "AI")


def test_cycle_is_rejected() -> None:
    cyclic = [
        Collection(1, "ONE", "One", 2, 1),
        Collection(2, "TWO", "Two", 1, 1),
    ]
    with pytest.raises(CollectionHierarchyError):
        build_collection_forest(cyclic)
