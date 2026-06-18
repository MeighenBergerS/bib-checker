# Quickstart

This page walks through a complete check → suggest → fix workflow on a small `.bib` file.

## 1 — Create a sample bib file

Save the following as `paper.bib`:

```bibtex
@article{Spolyar:2007qv,
    author = "Spolyar, Douglas and Freese, Katherine and Gondolo, Paolo",
    title = "{Dark matter and the first stars: a new phase of stellar evolution}",
    eprint = "0705.0521",
    archivePrefix = "arXiv",
    doi = "10.1103/PhysRevLett.100.051101",
    journal = "Phys. Rev. Lett.",
    volume = "100",
    pages = "051101",
    year = "2008"
}

@article{FakeKey:9999xx,
    author = "Nobody, Alice",
    title = "{This entry does not exist anywhere}",
    year = "1900"
}
```

## 2 — Run the check

```bash
bib-checker check paper.bib
```

Expected output:

```
Parsed 2 entries from paper.bib
╭─────────── Results: paper.bib ───────────╮
│ ✓ 1 ok   ✗ 1 missing   ⚠ 1 non-standard  │
╰──────────────────────────────────────────╯

  Citation key    Status
  ─────────────────────
  FakeKey:9999xx  ✗ missing  ⚠ non-std key

Wrote 1 flagged entries to results.json
```

The tool writes `results.json` containing only the flagged entries.

## 3 — Search for suggestions and generate the HTML report

```bash
bib-checker suggest results.json --html
```

This searches InspireHEP for replacement candidates and writes:

- `suggestions.json` — machine-readable list of candidates
- `report.html` — a visual report combining check results and suggestions

Open `report.html` in your browser to see the full output.

## 4 — Apply fixes

```bash
bib-checker fix paper.bib results.json --dry-run
```

The `--dry-run` flag shows what would change without writing anything. Remove it to
produce `paper_fixed.bib`:

```bash
bib-checker fix paper.bib results.json
```

`paper_fixed.bib` will contain:

- All clean entries first.
- A separator comment block followed by the entries that still need manual attention
  (missing or unfixable mismatches).

!!! tip "The source file is never modified"
    `fix` always writes to a new file (`paper_fixed.bib` by default). Use `--output`
    to choose a different path.

## What's next?

- [Check guide](../guides/check.md) — all flags and output format details.
- [Suggest guide](../guides/suggest.md) — how replacement candidates are ranked.
- [Fix guide](../guides/fix.md) — how to interpret the fixed bib and handle tricky cases.
- [Configuration](../guides/configuration.md) — skip entries, set rate limits, use ADS.
