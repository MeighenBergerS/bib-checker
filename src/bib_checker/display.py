"""Rich terminal display helpers for bib-checker output."""

from __future__ import annotations

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .models import CheckResult, Suggestion

console = Console()

# Status symbols and styles
_STATUS_STYLE: dict[str, tuple[str, str]] = {
    "ok": ("✓", "green"),
    "missing": ("✗", "bold red"),
    "mismatch": ("~", "bold yellow"),
}


def print_check_results(results: list[CheckResult], bib_name: str) -> None:
    """Print a rich summary table of check results.

    Parameters
    ----------
    results : list[CheckResult]
        Results returned by :func:`~bib_checker.checker.check_entries`.
    bib_name : str
        Display name of the source .bib file, shown in the panel title.
    """
    ok = [r for r in results if r.status == "ok"]
    missing = [r for r in results if r.status == "missing"]
    mismatch = [r for r in results if r.status == "mismatch"]

    # Summary panel
    summary = (
        f"[green]✓ {len(ok)} ok[/]   "
        f"[bold red]✗ {len(missing)} missing[/]   "
        f"[bold yellow]~ {len(mismatch)} mismatched[/]"
    )
    console.print(Panel(summary, title=f"[bold]Results: {bib_name}[/]", box=box.ROUNDED))

    # Only render the table when there is something flagged.
    flagged = missing + mismatch
    if not flagged:
        console.print("[green]All entries look good.[/]\n")
        return

    table = Table(box=box.SIMPLE_HEAVY, show_lines=True, highlight=True)
    table.add_column("Citation key", style="cyan", no_wrap=True)
    table.add_column("Status", justify="center", no_wrap=True)
    table.add_column("Mismatched fields", overflow="fold")

    for r in flagged:
        symbol, style = _STATUS_STYLE[r.status]
        status_str = f"[{style}]{symbol} {r.status}[/]"

        if r.mismatches:
            details = "\n".join(
                f"[bold]{m.field_name}[/]\n  local  : {m.local_value}\n  inspire: {m.inspire_value}"
                for m in r.mismatches
            )
        else:
            details = ""

        table.add_row(r.key, status_str, details)

    console.print(table)


def print_suggestions(suggestions: list[Suggestion]) -> None:
    """Print a rich summary table of replacement suggestions.

    Parameters
    ----------
    suggestions : list[Suggestion]
        Suggestions returned by
        :func:`~bib_checker.searcher.suggest_replacements`.
    """
    if not suggestions:
        console.print("[yellow]No suggestions found.[/]\n")
        return

    # Group by the key they target.
    by_key: dict[str, list[Suggestion]] = {}
    for s in suggestions:
        by_key.setdefault(s.for_key, []).append(s)

    for for_key, group in by_key.items():
        table = Table(
            box=box.SIMPLE_HEAVY,
            show_lines=True,
            title=f"Suggestions for [bold cyan]{for_key}[/]",
            highlight=True,
        )
        table.add_column("#", style="dim", width=3, justify="right")
        table.add_column("Texkey", style="cyan", no_wrap=True)
        table.add_column("Title", overflow="fold")
        table.add_column("First author", no_wrap=True)
        table.add_column("Year", justify="center", no_wrap=True)
        table.add_column("Eprint / DOI", overflow="fold")

        for i, s in enumerate(group, start=1):
            first_author = s.authors[0] if s.authors else "—"
            ref = s.eprint or s.doi or "—"
            table.add_row(str(i), s.texkey, s.title, first_author, s.year, ref)

        console.print(table)
