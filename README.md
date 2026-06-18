# bib-checker

Validate `.bib` citations against [InspireHEP](https://inspirehep.net) and fix what's wrong.

[![CI](https://github.com/MeighenBergerS/bib-checker/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/MeighenBergerS/bib-checker/actions/workflows/ci.yml)
[![Docs](https://github.com/MeighenBergerS/bib-checker/actions/workflows/docs.yml/badge.svg?branch=main)](https://meighenbergers.github.io/bib-checker/)
[![Python Versions](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)](https://www.python.org/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

|               |                                                 |
|---------------|-------------------------------------------------|
| Repository    | <https://github.com/MeighenBergerS/bib-checker> |
| Documentation | <https://meighenbergers.github.io/bib-checker/> |

## Summary

bib-checker is a Python CLI that checks every entry in a `.bib` file against the InspireHEP
database, flags missing or mismatched records, suggests canonical replacements, and writes a
corrected `.bib` file — all in three commands.

**Everything is on the [documentation site](https://meighenbergers.github.io/bib-checker/).**
Start there rather than reading the repository directly.

## Quick start

```bash
pip install --pre -e .

bib-checker check paper.bib             # Step 1 — find problems
bib-checker suggest results.json        # Step 2 — find replacements
bib-checker fix paper.bib results.json  # Step 3 — apply fixes
```

## Getting Help

Have a question or need help? Open a
[discussion](https://github.com/MeighenBergerS/bib-checker/discussions).

Found a bug or want to suggest a change?
[Open an issue](https://github.com/MeighenBergerS/bib-checker/issues/new).

## License

This repository is licensed under the GNU General Public License v3.0 or later (GPL-3.0-or-later).
See the [LICENSE](LICENSE) file.
