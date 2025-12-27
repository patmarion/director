To run tests:

uv sync --all-extras
uv run pytest  # run all tests
uv run pytest tests/file.py  # run a specific test file

To run format and linter:

uv sync --all-extras
uv run ruff format
uv run ruff check --fix

To build and view docs:

uv sync --all-extras
uv run docs/manage_docs.py build
uv run docs/manage_docs.py view
# optional, clean the docs generated files:
uv run docs/manage_docs.py clean
