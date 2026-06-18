# Check

The `check` subcommand is Step 1 of the workflow. It reads a `.bib` file, looks up
every citation key against InspireHEP, and writes a `results.json` file containing
only the flagged entries.

## Usage

```bash
bib-checker check FILE.bib [OPTIONS]
```

## Options

| Option | Default | Description |
|---|---|---|
| `--output FILE` | `results.json` | Where to write the flagged results. |
| `--reformat` | off | Also write a reformatted `.bib` with flagged entries at the end. |
| `--reformat-output FILE` | `<name>_reformatted.bib` | Output path for the reformatted bib. |
| `--html` | off | Write a self-contained HTML report alongside the JSON. |
| `--html-output FILE` | `<name>_report.html` | Output path for the HTML report. |
| `--no-cache` | off | Bypass the on-disk result cache and re-fetch all entries. |
| `--ads-token TOKEN` | `$ADS_TOKEN` | NASA ADS token for the ADS direct fallback. |
| `--delay SECONDS` | `0.5` | Delay between API requests (global flag, before subcommand). |
| `--verbose` | off | Print per-batch progress (global flag, before subcommand). |

## How it works

1. The `.bib` file is parsed into a list of entries.
2. Entries whose keys appear in the ignore list are skipped silently.
3. Remaining entries are batch-looked-up on InspireHEP (50 keys per request by default).
   Previously cached results are reused without hitting the network.
4. Each entry is flagged as:

   | Status | Meaning |
   |---|---|
   | `ok` | Found on InspireHEP; all compared fields match. |
   | `missing` | Not found by texkey on InspireHEP. |
   | `mismatch` | Found, but at least one of `doi`, `eprint`, `year`, `title` differs. |
   | `found_via_ads` | Missing by texkey but located via the `adsurl` bibcode. |
   | `mismatch_via_ads` | Found via ADS bibcode but fields differ. |

5. Only `missing`, `mismatch`, `found_via_ads`, and `mismatch_via_ads` entries are
   written to `results.json`. The `ok` entries are not included.

## Field comparison

Fields are compared after normalisation that handles LaTeX ↔ Unicode equivalences:

- Unicode Greek letters (e.g. `θ`) are mapped to their LaTeX command names (`theta`).
- `\ensuremath{...}` wrappers are stripped.
- Remaining `\command` sequences are replaced with the bare command name.
- Braces are removed; accents are stripped; text is lowercased.

This means `{\ensuremath{\theta_{13}}}` and `θ₁₃` are considered equal.

## On-disk cache

Results are cached in a hidden JSON file next to the `.bib`: `.{stem}-cache.json`.
Each cache slot stores a hash of the local entry's fields. If the entry changes, the
cached result is treated as stale and the entry is re-fetched.

Use `--no-cache` to bypass the cache entirely.

## ADS fallback

For entries that remain `missing` and have an `adsurl` field, two fallback tiers are
attempted automatically:

1. InspireHEP is queried using the ADS bibcode embedded in `adsurl`. On success the
   status becomes `found_via_ads`.
2. If an `--ads-token` is provided and tier 1 finds nothing, the ADS API is queried
   directly. Status becomes `ok_via_ads` or `mismatch_via_ads`.

## Non-standard keys

Citation keys that do not follow the InspireHEP `Author:YYYYxx` / `COLLAB:YYYYabc`
convention are flagged with `⚠ non-std key` in the console output. These entries
cannot be located by texkey lookup and will always appear as `missing`.
