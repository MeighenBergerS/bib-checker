# Suggest

The `suggest` subcommand is Step 2 of the workflow. It reads `results.json` produced
by `check` and searches InspireHEP for replacement candidates for each flagged entry.

## Usage

```bash
bib-checker suggest results.json [OPTIONS]
```

## Options

| Option | Default | Description |
|---|---|---|
| `--output FILE` | `suggestions.json` | Where to write the suggestions. |
| `--html` | off | Write a combined HTML report (check results + suggestions). |
| `--html-output FILE` | `report.html` | Output path for the HTML report. |
| `--delay SECONDS` | `0.5` | Delay between API requests (global flag). |

## How it works

For each actionable entry (status `missing` or `mismatch`), up to three search
queries are built in priority order:

1. `arxiv:<eprint>` — highest precision; used when the local entry has an eprint.
2. `doi:<doi>` — used when no eprint is available.
3. `a <surname> and date <year>` — author + year fallback.

The first query that returns results wins. Up to 5 suggestions are returned per entry.

## Output format

`suggestions.json` is a list of suggestion objects:

```json
[
  {
    "for_key": "FakeKey:9999xx",
    "texkey": "Real:2008ab",
    "local_title": "Title from your bib file",
    "title": "Title from InspireHEP",
    "authors": ["Author, A", "Author, B"],
    "year": "2008",
    "doi": "10.1/real",
    "eprint": "0800.0001",
    "inspire_id": "12345"
  }
]
```

The `for_key` field links each suggestion back to the original citation key.

!!! tip "Using with the HTML report"
    Running `bib-checker suggest results.json --html` is the most convenient workflow:
    it generates both `suggestions.json` (for scripting) and `report.html` (for
    human review) in one step.
