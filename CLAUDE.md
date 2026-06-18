# CLAUDE.md — bib-checker

A pip-installable Python CLI that validates `.bib` file citations against
[InspireHEP](https://inspirehep.net) and suggests or applies corrections.

---

## Project layout

```
src/bib_checker/
├── cli.py        # argparse entry points: check / suggest / fix
├── models.py     # BibEntry, CheckResult, FieldMismatch, Suggestion dataclasses
├── parser.py     # .bib parsing (bibtexparser v2); write_reformatted_bib
├── inspire.py    # InspireHEP REST API v1 client
├── checker.py    # Step 1: lookup, field comparison, normalisation, ADS fallback
├── searcher.py   # Step 2: build queries, rank candidates
├── fixer.py      # Step 3: patch mismatch fields, write _fixed.bib with separator
├── cache.py      # On-disk JSON cache keyed by texkey + field hash
├── config.py     # Load ignore list from pyproject.toml / .bibcheckerignore
├── ads.py        # NASA ADS REST API client (requires ADS_TOKEN)
├── display.py    # Rich console output helpers
└── report.py     # Self-contained HTML report generator

tests/
├── conftest.py               # Shared fixtures
├── fixtures/sample.bib
├── test_parser.py
├── test_checker.py           # HTTP mocked with `responses`
├── test_searcher.py          # HTTP mocked with `responses`
├── test_fixer.py
├── test_cache.py
├── test_config.py
├── test_cli.py
└── test_report.py
```

---

## Virtual environment

```bash
# Create and activate
python -m venv .venv
source .venv/bin/activate

# Install (--pre required for bibtexparser v2 beta)
pip install --pre -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=bib_checker
```

---

## CLI — three-step workflow

```bash
# Step 1: check a .bib file against InspireHEP
bib-checker check paper.bib [--output results.json] [--no-cache] [--ads-token TOKEN]
# → writes results.json (flagged entries only)
# → optional: --reformat  writes paper_reformatted.bib (flagged at end)
# → optional: --html       writes paper_report.html

# Step 2: search for replacement candidates
bib-checker suggest results.json [--output suggestions.json] [--html]
# → writes suggestions.json
# → with --html also writes report.html (combined check + suggestions)

# Step 3: apply InspireHEP canonical values to mismatch entries
bib-checker fix paper.bib results.json [--output paper_fixed.bib] [--fields doi,year] [--dry-run]
# → writes paper_fixed.bib by default (never modifies the source in-place)
# → clean entries first; still-flagged entries (missing + unfixable) at the end
#   separated by a comment block: "% These citations need validation/checking"
```

Global flags (before the subcommand): `--delay SECONDS` (default 0.5), `--verbose`.

---

## Design decisions

### Language and dependencies
- **Python 3.11+** — uses `tomllib` (stdlib), `match` not used but 3.11 type hints are.
- **No pydantic, no click** — plain `dataclasses` + `argparse`; minimal install footprint.
- **`requests` over `httpx`** — synchronous only, no async needed at this scale.
- **`rich`** — console output and tables only; no runtime complexity overhead.
- **`bibtexparser` v2 (beta)** — install with `pip install --pre`. API differs from v1:
  - `entry.entry_type` (not `.type`)
  - `entry.fields_dict` returns `Field` objects → extract `.value`
  - Must use `bibtexparser.parse_file()` / `bibtexparser.write_string()`

### Linting and formatting — ruff
Config lives in `pyproject.toml`:
```toml
[tool.ruff]
line-length = 100

[tool.ruff.lint]
select = ["E", "W", "F", "I", "UP", "B"]
ignore = ["E501"]   # line length enforced by formatter, not linter

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["S101"]  # allow assert in tests
```
Run `ruff check .` and `ruff format .` before committing.

### Docstrings
All public functions use **NumPy-style** docstrings (consistent with mkdocstrings
auto-generated API docs). Private helpers need at least a one-line summary.

### Field comparison and normalisation (`checker._normalise`)
Fields `doi`, `eprint`, `year`, `title` are compared after normalisation:
1. Unicode Greek letters (`θ`, `Γ`, …) → their LaTeX command names (`theta`, `gamma`, …)
2. `\ensuremath{...}` stripped (inner content kept)
3. Remaining `\command` sequences → bare command name
4. Braces `{}` removed
5. Combining accent marks stripped via `unicodedata.normalize("NFD")` + category filter
6. Lowercased, whitespace collapsed

This makes e.g. `{\ensuremath{\theta_{13}}}` and `θ₁₃` compare equal.

### InspireHEP API
- Base: `https://inspirehep.net/api`
- Texkey lookup (batched ORs): `GET /literature?q=texkey:A or texkey:B&fields=...`
- Batch size: 50 keys per request (configurable via `batch_size` arg)
- Rate limiting: 0.5 s between requests (global `--delay`)
- Relevant metadata fields: `texkeys`, `titles`, `authors`, `dois`,
  `arxiv_eprints`, `publication_info`, `external_system_identifiers`

### On-disk cache (`cache.CheckCache`)
- JSON file next to the `.bib`: `.{stem}-cache.json` (hidden, gitignored via `*.json`).
- Each slot stores: `entry_hash` (16-hex SHA-256 of the local fields dict) + serialised `CheckResult`.
- A result is treated as **stale** if `entry_hash` doesn't match the current local fields.
- Cache version tag (`_CACHE_VERSION = 2`) invalidates old formats on load.
- Bypass with `--no-cache`.

### ADS fallback (`checker.check_entries`)
For entries that remain `"missing"` after the InspireHEP pass and have an `adsurl` field:
1. **Tier 1** — InspireHEP queried by the ADS bibcode extracted from `adsurl`.
   On success: status → `"found_via_ads"`.
2. **Tier 2** — ADS API queried directly (requires `ADS_TOKEN` env var or `--ads-token`).
   On success: status → `"ok_via_ads"` or `"mismatch_via_ads"`.

### Ignore list (`config.load_ignore_keys`)
Keys can be excluded from checking via two sources (merged):
1. `.bibcheckerignore` file — searched next to the `.bib` first, then in `cwd`.
   One key per line; `#` comments and blank lines ignored.
2. `[tool.bib-checker] ignore = [...]` in `pyproject.toml` (upward search from `cwd`).

### fix output layout (`fixer.apply_fixes`)
- **Default output**: `<stem>_fixed.<ext>` — never overwrites the source file.
- After patching mismatch entries, `write_reformatted_bib` is used to place
  **still-flagged keys** (missing entries + mismatches with no InspireHEP record)
  at the end of the file, separated by:
  ```
  % ##########################################################################
  % These citations need validation/checking
  % ##########################################################################
  ```
- Returns `(applied: list[dict], still_flagged: set[str])`.

---

## Output formats

**`results.json`** (Step 1 → Step 2 input):
```json
[{
  "key": "FakeKey:9999xx",
  "status": "missing",
  "nonstandard_key": true,
  "mismatches": [],
  "local_entry": {"key": "...", "type": "article", "title": "...", "year": "1900"},
  "inspire_record": null
}]
```
Statuses written: `"missing"`, `"mismatch"`, `"found_via_ads"`, `"mismatch_via_ads"`.

**`suggestions.json`** (Step 2 output):
```json
[{
  "for_key": "FakeKey:9999xx",
  "texkey": "Real:2008ab",
  "local_title": "...",
  "title": "...",
  "authors": ["Author, A", "Author, B"],
  "year": "2008",
  "doi": "10.1/x",
  "eprint": "0800.0001",
  "inspire_id": "12345"
}]
```

---

## Common gotchas

- **`pip install --pre`** is required for bibtexparser v2 beta — omitting it silently
  installs v1 which has a completely different API.
- **`Field.value`** — `entry.fields_dict` returns `Field` objects, not strings.
  Always access `.value`.
- **`*.json` is gitignored** — this is intentional (output files are ephemeral).
  Test fixtures that need JSON should live in `tests/fixtures/` with a non-json extension
  or be created at runtime via `tmp_path`.
- **HTTP mocking** — use the `responses` library (not `pytest-httpx` or `unittest.mock`).
  Activate per-test with `@responses.activate` or `@rsps_lib.activate`.
- **`_CACHE_VERSION`** — bump this in `cache.py` whenever the cache schema changes,
  to avoid silent corruption of existing caches.
- **Conventional commits** — use `feat:`, `fix:`, `docs:`, `test:`, `chore:`, `refactor:`.

---

## Git conduct

- Do **not** add the agent as a co-author (`Co-authored-by:`, `Signed-off-by:`, etc.).
- Commits and PRs are attributed solely to the human author.
- Never force-push `main`.
