# Contributing

Use Python 3.10 or newer. Create a virtual environment, install `-e ".[dev]"`, and run `ruff format --check .`, `ruff check .`, `mypy`, and `pytest`.

Keep the safety invariants intact: previews must not mutate files, moves must never overwrite, and undo must stop when an original path is occupied. Add focused tests for behavior changes.

