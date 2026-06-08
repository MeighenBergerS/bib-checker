---
name: bib-checker
description: "Expert knowledge for the bib-checker Python project. Use when: working on bib-checker; adding features; debugging citation checking; modifying InspireHEP API logic; writing tests; changing the CLI; updating the bib parser; working on Step 1 (check) or Step 2 (suggest) workflows."
---

# bib-checker Project

A pip-installable Python CLI that validates `.bib` file citations against InspireHEP and suggests replacements.

## Project Layout

```
/home/smeighenberger/projects/bib-checker/
├── pyproject.toml
├── README.md
├── .gitignore
├── .venv/                        # Python 3.12 venv
├── bibliography.bib              # Local test bib file
└── src/bib_checker/
    ├── __init__.py
    ├── cli.py        # argparse entry points: `check` and `suggest`
    ├── models.py     # Dataclasses: BibEntry, CheckResult, FieldMismatch, Suggestion
    ├── parser.py     # .bib parsing via bibtexparser v2
    ├── inspire.py    # InspireHEP REST API v1 client (requests)
    ├── checker.py    # Step 1: check entries, compare fields, flag missing/mismatch
    └── searcher.py   # Step 2: load results.json, search for replacement candidates
tests/
├── fixtures/sample.bib
├── test_parser.py
├── test_checker.py   # mocked with `responses` library
└── test_searcher.py  # mocked with `responses` library
```

## Dependencies

| Package | Purpose |
|---|---|
| `bibtexparser>=2.0.0b7` | Parse `.bib` files (install with `--pre`) |
| `requests>=2.32` | HTTP calls to InspireHEP API |
| `pytest`, `responses`, `pytest-mock` | Dev/test only |

## Virtual Environment

```bash
# Activate
source .venv/bin/activate

# Install (requires --pre for bibtexparser v2 beta)
pip install --pre -e ".[dev]"

# Run tests
.venv/bin/pytest

# Run CLI
.venv/bin/bib-checker check bibliography.bib --verbose
.venv/bin/bib-checker suggest results.json --verbose
```

## Key Design Decisions

- **No pydantic, no click** — minimal deps; plain `dataclasses` + `argparse`
- **`requests` over `httpx`** — sync only; no async needed at this stage
- **`bibtexparser` v2** — `entry.entry_type` (not `.type`); `fields_dict` returns `Field` objects, extract `.value`
- **Field comparison** normalised: lowercased, accent-stripped, whitespace-collapsed
- **Fields compared**: `doi`, `eprint`, `year`, `title`
- **Rate limiting**: 0.5 s delay between requests (configurable via `--delay`)

## InspireHEP API

- Base: `https://inspirehep.net/api`
- Texkey lookup: `GET /literature?q=texkey:<KEY>&fields=texkeys,titles,...`
- Search: `GET /literature?q=<QUERY>&size=5&sort=mostrecent`
- Response shape: `{"hits": {"hits": [{"id": "...", "metadata": {...}}]}}`
- Relevant metadata fields: `texkeys`, `titles`, `authors`, `dois`, `arxiv_eprints`, `publication_info`

## Step 1 — `check`

1. Parse `.bib` → list of `BibEntry`
2. For each entry: `InspireClient.lookup_by_texkey(entry.key)`
3. Not found → `status="missing"`; found → compare fields → `status="ok"` or `"mismatch"`
4. Write only `missing`/`mismatch` results to `results.json`

## Step 2 — `suggest`

1. Load `results.json`
2. For each actionable entry, build search queries in priority order:
   - `arxiv:<eprint>` (highest precision)
   - `doi:<doi>`
   - `a <surname> and date <year>`
3. First query with hits wins; up to 5 suggestions per entry
4. Write to `suggestions.json`

## Output Formats

**results.json** (Step 1 output / Step 2 input):
```json
[{"key": "FakeKey:9999xx", "status": "missing", "mismatches": [], "local_entry": {...}, "inspire_record": null}]
```

**suggestions.json** (Step 2 output):
```json
[{"for_key": "FakeKey:9999xx", "texkey": "Real:2008ab", "title": "...", "authors": [...], "year": "2008", "doi": "...", "eprint": "...", "inspire_id": "..."}]
```

## Common Gotchas

- `bibtexparser` v2 is still in beta → always install with `pip install --pre`
- `Entry.fields_dict` values are `Field` objects → access `.value` to get the string
- `Entry.entry_type` (not `.type`)
- The `.gitignore` intentionally ignores `*.json` (output files) — don't override for fixtures
- Test HTTP mocking uses the `responses` library (not `pytest-httpx`)

## Git and PR Conduct

- Do **not** add yourself (the agent) as a co-author in commit messages or PR descriptions.
- Do **not** include `Co-authored-by:` trailers, `Signed-off-by:` lines, or any other attribution that names the agent in commits or PRs.
- Commits and PRs are attributed solely to the human author.
