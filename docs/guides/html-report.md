# HTML Report

Both `check` and `suggest` can produce a self-contained HTML report. It is the most
convenient way to review results at a glance.

## Generating the report

**From `check` (check results only, no suggestions):**

```bash
bib-checker check paper.bib --html
# → paper_report.html
```

**From `suggest` (check results + suggestions combined):**

```bash
bib-checker suggest results.json --html
# → report.html
```

Use `--html-output <path>` in either command to choose a custom output path.

## What's in the report

The report is a single `.html` file with no external dependencies — it can be opened
offline and shared as an attachment.

**Summary pills** — at the top: counts of ok / missing / mismatched / non-standard entries.

**Flagged entries table** — one row per flagged entry showing:

- Citation key
- Status badge (`missing` or `mismatch`)
- For mismatches: a diff of each field that differs (local value vs InspireHEP value)

**Replacement suggestions** — grouped by citation key, showing:

- Suggested InspireHEP texkey (linked to the InspireHEP record)
- Suggested title, first author, year
- ArXiv eprint link or DOI

## Example workflow

```bash
# Run everything and open the report
bib-checker check paper.bib
bib-checker suggest results.json --html
open report.html          # macOS
xdg-open report.html      # Linux
start report.html         # Windows
```
