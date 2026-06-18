# Fix

The `fix` subcommand is Step 3 of the workflow. It reads the original `.bib` file and
`results.json`, applies InspireHEP canonical values to mismatched entries, and writes a
new `.bib` file.

## Usage

```bash
bib-checker fix FILE.bib results.json [OPTIONS]
```

## Options

| Option | Default | Description |
|---|---|---|
| `--output FILE` | `<name>_fixed.bib` | Output path for the fixed bib. |
| `--fields FIELDS` | `doi,eprint,year,title` | Comma-separated list of fields to update. |
| `--dry-run` | off | Show what would change without writing anything. |

## How it works

1. Only entries with `status == "mismatch"` that have an `inspire_record` are patched.
   `missing` entries cannot be auto-fixed (there is no record to copy from).
2. For each mismatch entry, the specified fields are updated to InspireHEP's canonical values.
3. The output file is structured in two sections:

   - **Main section** — all entries that are now clean (both originally-ok and freshly fixed).
   - **Separator** — a comment block marking the boundary.
   - **Flagged section** — entries that still need manual attention:
     - All `missing` entries.
     - Mismatch entries where `fix` found no fixable InspireHEP record.

The separator looks like:

```bibtex
% ##########################################################################
% These citations need validation/checking
% ##########################################################################
```

!!! warning "The source file is never modified"
    `fix` always writes to a new file (`<name>_fixed.bib` by default). The original
    `.bib` is read-only from `fix`'s perspective.

## Reviewing fixes before applying

Always use `--dry-run` first to inspect what will change:

```bash
bib-checker fix paper.bib results.json --dry-run
```

Pay special attention to entries where **all** of `eprint`, `year`, and `title` differ —
this usually means InspireHEP's record for that texkey points to a different paper, and
the fix would be wrong.

## Restricting which fields are updated

Use `--fields` to update only a subset of fields:

```bash
# Fix only the year, leave title and DOI alone
bib-checker fix paper.bib results.json --fields year
```

## After running fix

The entries at the end of `<name>_fixed.bib` (after the separator) still need manual
attention. Common actions:

- **Wrong texkey** — if InspireHEP's record for that key is a different paper, find the
  correct texkey using `report.html` (the `suggest` step usually identifies it) and
  rename the key in both the `.bib` and your `.tex` files.
- **Non-HEP entries** — books, technical reports, and web references may never be on
  InspireHEP. Consider adding them to your `.bibcheckerignore` file.
- **Preprints without a texkey** — entries with non-standard keys (e.g. `chan2024first`)
  cannot be looked up; rename them to the InspireHEP convention.
