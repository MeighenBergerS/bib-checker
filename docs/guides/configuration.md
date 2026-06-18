# Configuration

## Ignoring entries

Some entries will never appear on InspireHEP — books, technical reports, web references,
or entries with non-standard keys you don't plan to fix. Add them to an ignore list so
`check` skips them silently.

### Option 1 — `.bibcheckerignore` file

Create a `.bibcheckerignore` file next to your `.bib` file (or in the current working
directory). One citation key per line; lines starting with `#` are comments.

```
# Books and references not on InspireHEP
Cramer1946
Fisher1925
AkademikLomonosov

# Checked manually — OK
JUNO:2022kdp
```

### Option 2 — `pyproject.toml`

Add an ignore list to your project's `pyproject.toml`:

```toml
[tool.bib-checker]
ignore = [
    "Cramer1946",
    "Fisher1925",
    "AkademikLomonosov",
]
```

Both sources are merged — you can use one or both.

## NASA ADS fallback

For entries that have an `adsurl` field (common in bib files exported from ADS),
`bib-checker` can look them up via the ADS bibcode embedded in the URL.

**Tier 1 (automatic):** InspireHEP is queried by the ADS bibcode. No token required.

**Tier 2 (requires token):** If tier 1 fails, the ADS API is queried directly. Set
your token via environment variable or CLI flag:

```bash
# Environment variable (recommended — add to your shell profile)
export ADS_TOKEN=your_token_here

# Per-run flag
bib-checker check paper.bib --ads-token your_token_here
```

Get a free ADS token at [ui.adsabs.harvard.edu/user/settings/token](https://ui.adsabs.harvard.edu/user/settings/token).

## Rate limiting

By default, bib-checker waits 0.5 seconds between API requests. Increase this if you
experience throttling errors:

```bash
bib-checker --delay 1.0 check paper.bib
```

The `--delay` flag is global and must appear **before** the subcommand.

## Caching

Results are cached in a hidden JSON file next to your `.bib`:

```
.main-cache.json   ← for main.bib
```

The cache stores a hash of each entry's fields. If an entry changes, its cached result
is discarded and the entry is re-fetched on the next run.

To bypass the cache entirely:

```bash
bib-checker check paper.bib --no-cache
```
