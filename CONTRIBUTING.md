# Contributing

Contributions are welcome. Please keep Zotero access strictly read-only and add
tests for behavior changes.

```bash
python -m pip install -e '.[dev]'
pytest
```

Public functions require type hints and docstrings. Prefer small, readable
modules and avoid dependencies when the standard library is sufficient.
