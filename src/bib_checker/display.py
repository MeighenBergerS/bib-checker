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
    "found_via_ads": ("→", "bold blue"),
    "ok_via_ads": ("✓", "bold cyan"),
    "mismatch_via_ads": ("~", "bold cyan"),
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
    ok_via_ads = [r for r in results if r.status == "ok_via_ads"]
    missing = [r for r in results if r.status == "missing"]
    mismatch = [r for r in results if r.status == "mismatch"]
    found_via_ads = [r for r in results if r.status == "found_via_ads"]
    mismatch_via_ads = [r for r in results if r.status == "mismatch_via_ads"]
    nonstandard = [r for r in results if r.nonstandard_key]

    # Summary panel
    summary = (
        f"[green]✓ {len(ok)} ok[/]   "
        f"[bold red]✗ {len(missing)} missing[/]   "
        f"[bold yellow]~ {len(mismatch)} mismatched[/]"
    )
    if ok_via_ads:
        summary += f"   [bold cyan]✓ {len(ok_via_ads)} ok via ADS[/]"
    if found_via_ads:
        summary += f"   [bold blue]→ {len(found_via_ads)} found via ADS[/]"
    if mismatch_via_ads:
        summary += f"   [bold cyan]~ {len(mismatch_via_ads)} mismatched via ADS[/]"
    if nonstandard:
        summary += f"   [bold magenta]⚠ {len(nonstandard)} non-standard key(s)[/]"
    console.print(Panel(summary, title=f"[bold]Results: {bib_name}[/]", box=box.ROUNDED))

    # Only render the table when there is something flagged.
    flagged = missing + mismatch + found_via_ads + mismatch_via_ads
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
        if r.nonstandard_key:
            status_str += "\n[bold magenta]⚠ non-std key[/]"

        if r.status == "found_via_ads" and r.inspire_record:
            inspire_key = (r.inspire_record.get("metadata", {}).get("texkeys") or [""])[0]
            details = f"[bold blue]InspireHEP key:[/] {inspire_key}\n"
        else:
            details = ""

        if r.mismatches:
            details += "\n".join(
                f"[bold]{m.field_name}[/]\n  local : {m.local_value}\n  remote: {m.remote_value}"
                for m in r.mismatches
            )

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
        local_title = group[0].local_title or "(no title in bib)"
        console.print(f"[dim]Local title:[/] [italic]{local_title}[/]")

        table = Table(
            box=box.SIMPLE_HEAVY,
            show_lines=True,
            title=f"Suggestions for [bold cyan]{for_key}[/]",
            highlight=True,
        )
        table.add_column("#", style="dim", width=3, justify="right")
        table.add_column("Texkey", style="cyan", no_wrap=True)
        table.add_column("Suggested title", overflow="fold")
        table.add_column("First author", no_wrap=True)
        table.add_column("Year", justify="center", no_wrap=True)
        table.add_column("Eprint / DOI", overflow="fold")

        for i, s in enumerate(group, start=1):
            first_author = s.authors[0] if s.authors else "—"
            ref = s.eprint or s.doi or "—"
            table.add_row(str(i), s.texkey, s.title, first_author, s.year, ref)

        console.print(table)
