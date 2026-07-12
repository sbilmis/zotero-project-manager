"""Collection tree construction, lookup, and traversal."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from pathlib import Path

from .filenames import sanitize_component
from .models import Collection, CollectionNode


class CollectionError(ValueError):
    """Base class for collection lookup and hierarchy errors."""


class CollectionNotFoundError(CollectionError):
    """Raised when a collection selector has no match."""


class AmbiguousCollectionError(CollectionError):
    """Raised when a collection name matches more than one collection."""


class CollectionHierarchyError(CollectionError):
    """Raised when Zotero collection relationships contain a cycle."""


def build_collection_forest(collections: Iterable[Collection]) -> list[CollectionNode]:
    """Build a sorted forest from flat Zotero collection records."""

    records = list(collections)
    nodes = {collection.id: CollectionNode(collection) for collection in records}
    roots: list[CollectionNode] = []
    for collection in records:
        node = nodes[collection.id]
        if collection.parent_id is None or collection.parent_id not in nodes:
            roots.append(node)
        else:
            nodes[collection.parent_id].children.append(node)

    _assert_acyclic(nodes.values())
    _sort_nodes(roots)
    return roots


def _assert_acyclic(nodes: Iterable[CollectionNode]) -> None:
    state: dict[int, int] = {}

    def visit(node: CollectionNode) -> None:
        marker = state.get(node.collection.id, 0)
        if marker == 1:
            raise CollectionHierarchyError("Collection hierarchy contains a cycle")
        if marker == 2:
            return
        state[node.collection.id] = 1
        for child in node.children:
            visit(child)
        state[node.collection.id] = 2

    for node in nodes:
        visit(node)


def _sort_nodes(nodes: list[CollectionNode]) -> None:
    nodes.sort(key=lambda node: (node.collection.name.casefold(), node.collection.key))
    for node in nodes:
        _sort_nodes(node.children)


def resolve_collection(collections: Iterable[Collection], selector: str) -> Collection:
    """Resolve a collection by exact key or case-insensitive full name."""

    records = list(collections)
    key_matches = [record for record in records if record.key == selector]
    if key_matches:
        return key_matches[0]

    name_matches = [record for record in records if record.name.casefold() == selector.casefold()]
    if not name_matches:
        raise CollectionNotFoundError(f"No Zotero collection matches {selector!r}")
    if len(name_matches) > 1:
        keys = ", ".join(record.key for record in name_matches)
        raise AmbiguousCollectionError(
            f"Collection name {selector!r} is ambiguous; use one of these keys: {keys}"
        )
    return name_matches[0]


def find_node(forest: Iterable[CollectionNode], collection_id: int) -> CollectionNode:
    """Find a collection node by numeric ID."""

    for node in walk_nodes(forest):
        if node.collection.id == collection_id:
            return node
    raise CollectionNotFoundError(f"No Zotero collection has ID {collection_id}")


def walk_nodes(nodes: Iterable[CollectionNode]) -> Iterator[CollectionNode]:
    """Yield collection nodes depth-first."""

    for node in nodes:
        yield node
        yield from walk_nodes(node.children)


def collection_paths(root: CollectionNode, *, recursive: bool = True) -> dict[int, Path]:
    """Map a selected collection and descendants to unique relative paths."""

    result: dict[int, Path] = {root.collection.id: Path()}
    if not recursive:
        return result

    def add_children(node: CollectionNode, parent: Path) -> None:
        reserved: set[str] = set()
        for child in node.children:
            name = sanitize_component(child.collection.name)
            candidate = name
            if candidate.casefold() in reserved:
                candidate = f"{name} [{child.collection.key}]"
            reserved.add(candidate.casefold())
            path = parent / candidate
            result[child.collection.id] = path
            add_children(child, path)

    add_children(root, Path())
    return result


def format_collection_forest(forest: Iterable[CollectionNode]) -> str:
    """Format collections as an indented CLI tree including Zotero keys."""

    lines = ["My Library"]

    def append(nodes: Iterable[CollectionNode], depth: int) -> None:
        for node in nodes:
            lines.append(f"{'    ' * depth}{node.collection.name} [{node.collection.key}]")
            append(node.children, depth + 1)

    append(forest, 1)
    return "\n".join(lines)
