To run tests:

uv sync --all-extras
uv run pytest tests/file.py

To run format and check linter:

uv sync --all-extras
uv run ruff format
uv run ruff check

To build and view docs:

uv sync --all-extras
uv run ./manage_docs.py build
uv run ./manage_docs.py view
