# bib-checker

Validate citations in a LaTeX `.bib` file against InspireHEP and suggest replacements for entries that are missing or mismatched.

## Requirements

- Python ≥ 3.11
- [`bibtexparser`](https://bibtexparser.readthedocs.io/) v2
- [`requests`](https://requests.readthedocs.io/)

## Installation

```bash
pip install -e ".[dev]"   # include dev/test dependencies
# or
pip install -e .           # runtime only
```

## Usage

### Step 1 — check your bib file

```bash
bib-checker check bibliography.bib
# writes flagged entries (missing / mismatched) to results.json
```

Options:

| Flag | Default | Description |
|------|---------|-------------|
| `--output FILE` | `results.json` | Where to write flagged entries |
| `--delay SECONDS` | `0.5` | Pause between API requests |
| `--verbose` | off | Print progress for each entry |

### Step 2 — find replacement candidates

```bash
bib-checker suggest results.json
# writes ranked candidate records to suggestions.json
```

Options:

| Flag | Default | Description |
|------|---------|-------------|
| `--output FILE` | `suggestions.json` | Where to write suggestions |
| `--delay SECONDS` | `0.5` | Pause between API requests |
| `--verbose` | off | Print progress for each entry |

## Output format

**`results.json`** — array of flagged entries:

```json
[
  {
    "key": "FakeKey:9999xx",
    "status": "missing",
    "mismatches": [],
    "local_entry": { "key": "...", "type": "article", "doi": "..." },
    "inspire_record": null
  }
]
```

`status` is one of `"missing"` (not found on InspireHEP) or `"mismatch"` (found but fields differ).

**`suggestions.json`** — array of candidates:

```json
[
  {
    "for_key": "FakeKey:9999xx",
    "texkey": "Spolyar:2007qv",
    "title": "Dark matter and the first stars …",
    "authors": ["Spolyar, Douglas", "Freese, Katherine", "Gondolo, Paolo"],
    "year": "2008",
    "doi": "10.1103/PhysRevLett.100.051101",
    "eprint": "0705.0521",
    "inspire_id": "123456"
  }
]
```

## Running tests

```bash
pytest
# skip integration (live network) tests
pytest -m "not integration"
```

## Project layout

```
src/bib_checker/
├── cli.py       # argparse entry points
├── parser.py    # .bib file parsing
├── models.py    # dataclasses
├── inspire.py   # InspireHEP API client
├── checker.py   # Step 1 logic
└── searcher.py  # Step 2 logic
tests/
├── fixtures/sample.bib
├── test_parser.py
├── test_checker.py
└── test_searcher.py
```
