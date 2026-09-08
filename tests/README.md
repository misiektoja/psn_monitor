# Offline test suite

These tests never touch the network or the PlayStation Network. They assert the repository's own
metadata, so a change that breaks the citation, the sponsor button, the declared editor style or the
release integrity of a published archive fails before it reaches a release.

## Running

From the repository root:

```bash
pip install -e '.[test]'
python -m pytest
```

`pyproject.toml` puts the repository root first on `sys.path`, so the tests always read the working tree.

## Layout

| File | Area under test |
| --- | --- |
| `test_repository_metadata.py` | Governance files, citation, funding, line endings, the declared editor style, the pinned linter and release integrity |

## Conventions

* Keep every test offline
* Read repository files through the `read_asset` and `read_yaml_asset` helpers
* Skip rather than fail when the checkout is not a Git working tree
