# Contributing to bib-checker

Thank you for considering a contribution to bib-checker!

The types of contributions most welcome are:

- Bug reports and reproducible examples.
- Enhancement suggestions.
- Code fixes and new features.
- Documentation improvements.

## Reporting Bugs and Suggesting Enhancements

Open an issue using the appropriate template from the
[issue chooser](https://github.com/MeighenBergerS/bib-checker/issues/new/choose).

> [!TIP]
> When reporting bugs, include your OS, Python version, the exact command
> you ran, and the full error output.

## Making Code Changes

1. Fork the repository and create a branch from `main`.
2. Set up your development environment:

```sh
python3 -m venv .venv
source .venv/bin/activate
```

```sh
pip install --pre -e ".[dev]"
```

3. Make your changes. Add or update tests in `tests/` for any new behaviour.
4. Run the full test suite locally before opening a PR:

```sh
pytest
```

5. Open a pull request against `main`. Fill in the PR template.

## Code Style

- Python 3.11+, formatted with `ruff` (line length 100).
- All public functions and classes must have NumPy-style docstrings.
- Private helpers (prefixed `_`) should have at least a one-line summary docstring.

## Commit Messages

Use the conventional commit format:

```
type: short summary in present tense

Optional longer body explaining the why.
```

Common types: `feat`, `fix`, `docs`, `test`, `chore`, `refactor`.

## Code of Conduct

Please read and follow the [Code of Conduct](CODE_OF_CONDUCT.md).
