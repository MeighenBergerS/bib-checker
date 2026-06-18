# Contributing

Thank you for contributing to bib-checker!

## Setup

```bash
git clone https://github.com/MeighenBergerS/bib-checker.git
cd bib-checker
python -m venv .venv
source .venv/bin/activate
pip install --pre -e ".[dev]"
```

## Workflow

1. Fork the repository and create a branch from `main`.
2. Make your changes and add tests.
3. Run the test suite:
   ```bash
   pytest
   # With coverage:
   pytest --cov=bib_checker
   ```
4. Run the linter:
   ```bash
   ruff check .
   ruff format .
   ```
5. Open a pull request against `main`.

## Code style

- **Python 3.11+** with full type hints.
- **Line length**: 100 characters (enforced by `ruff format`).
- **Linting rules**: `E`, `W`, `F`, `I`, `UP`, `B` (see `pyproject.toml`).
- **Docstrings**: NumPy style for all public APIs. Private helpers need at least a
  one-line summary.

## Testing

- Unit tests use `pytest`.
- HTTP calls to InspireHEP are mocked with the `responses` library — never make real
  network calls in tests.
- Place shared fixtures in `tests/conftest.py`.
- New `.bib` fixture files go in `tests/fixtures/`.

## Commit messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>: <short summary>

[optional body]
```

Common types: `feat`, `fix`, `docs`, `test`, `chore`, `refactor`.

## Building the docs

```bash
mkdocs serve        # live-preview at http://127.0.0.1:8000
mkdocs build        # static output in site/
```
