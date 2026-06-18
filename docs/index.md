# bib-checker

`bib-checker` is a command-line tool that validates `.bib` file citations against
[InspireHEP](https://inspirehep.net) and suggests or applies corrections.

---

## What it does

1. **Check** — looks up every citation key against InspireHEP by texkey and flags
   entries that are missing or have mismatched fields (`doi`, `eprint`, `year`, `title`).
2. **Suggest** — searches InspireHEP for replacement candidates for every flagged entry.
3. **Fix** — applies InspireHEP canonical values to mismatched entries and writes a new
   `.bib` file with still-problematic entries separated at the end for manual review.

---

## Quick example

```bash
# Step 1 — check all entries and write a results file
bib-checker check paper.bib

# Step 2 — find replacement candidates and generate an HTML report
bib-checker suggest results.json --html

# Step 3 — apply fixes; outputs paper_fixed.bib
bib-checker fix paper.bib results.json
```

Open `report.html` in your browser for a visual summary of every flagged entry and its
suggested replacement.

---

## Design goals

- **Zero friction** — a single `pip install` and three commands are all you need.
- **Non-destructive** — the source `.bib` file is never modified in-place.
- **Transparent** — every suggested change is shown as a diff before anything is written.
- **Minimal dependencies** — `bibtexparser`, `requests`, and `rich`; no heavy frameworks.

---

## Next steps

- [Installation](getting-started/installation.md) — how to install and set up the tool.
- [Quickstart](getting-started/quickstart.md) — a full end-to-end walkthrough.
- [Configuration](guides/configuration.md) — ignore lists, ADS token, pyproject.toml config.
