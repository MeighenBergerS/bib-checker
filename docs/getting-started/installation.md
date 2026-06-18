# Installation

## Requirements

- Python 3.11 or newer
- An internet connection (InspireHEP API calls are made at check time)

## Install from source

```bash
# Clone the repository
git clone https://github.com/MeighenBergerS/bib-checker.git
cd bib-checker

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\activate           # Windows

# Install the package and all dependencies
# --pre is required: bibtexparser v2 is still in beta
pip install --pre -e ".[dev]"
```

!!! warning "The `--pre` flag is required"
    `bibtexparser` v2 is still a pre-release. Without `--pre`, `pip` will silently
    install v1, which has a completely different API and will cause import errors.

## Verify the installation

```bash
bib-checker --help
```

You should see:

```
usage: bib-checker [-h] [--delay SECONDS] [--verbose] {check,suggest,fix} ...
```

## Installing for development

The `[dev]` extra installs the test suite, linter, and documentation tools:

| Package | Purpose |
|---|---|
| `pytest`, `pytest-cov` | Testing and coverage |
| `responses` | Mock HTTP calls in tests |
| `ruff` | Linting and formatting |
| `mkdocs`, `mkdocstrings[python]` | Documentation |

To build and serve the docs locally:

```bash
mkdocs serve
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.
