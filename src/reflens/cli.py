"""RefLens CLI -- ingest and explore papers from the terminal."""

import asyncio
import logging
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from reflens.config import get_settings
from reflens.core.engine import RefLensEngine

console = Console()


def _get_engine() -> RefLensEngine:
    return RefLensEngine(get_settings())


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging")
def main(verbose: bool) -> None:
    """RefLens -- AI-powered scientific paper database."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


@main.command()
@click.argument("pdf_path", type=click.Path(exists=True, path_type=Path))
@click.option("--notes", "-n", help="Personal notes about the paper")
@click.option(
    "--status",
    "-s",
    type=click.Choice(["unread", "partial", "read"]),
    default="unread",
    help="Reading status",
)
def ingest(pdf_path: Path, notes: str | None, status: str) -> None:
    """Ingest a PDF paper into the database."""
    engine = _get_engine()

    with console.status(f"Extracting from {pdf_path.name}..."):
        result = engine.ingest_paper(pdf_path, notes=notes, reading_status=status)

    console.print("\n[bold green]Paper ingested successfully![/bold green]")
    console.print(f"  ID:      {result['id']}")
    console.print(f"  Title:   {result['title']}")
    console.print(f"  Year:    {result['year'] or 'unknown'}")
    console.print(f"  Authors: {', '.join(result['authors']) or 'none'}")
    console.print(f"  Refs:    {result['citations_count']}")


@main.command()
@click.argument("folder", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--notes", "-n", help="Notes to attach to all papers")
def ingest_folder(folder: Path, notes: str | None) -> None:
    """Ingest all PDFs in a folder."""
    engine = _get_engine()
    pdfs = list(folder.glob("*.pdf"))

    if not pdfs:
        console.print(f"[yellow]No PDF files found in {folder}[/yellow]")
        return

    console.print(f"Found {len(pdfs)} PDF files")
    success = 0
    failed = 0

    for pdf in pdfs:
        try:
            with console.status(f"Processing {pdf.name}..."):
                result = engine.ingest_paper(pdf, notes=notes)
            console.print(f"  [green]OK[/green] {result['title']}")
            success += 1
        except Exception as e:
            console.print(f"  [red]FAIL[/red] {pdf.name}: {e}")
            failed += 1

    console.print(f"\nDone: {success} ingested, {failed} failed")


@main.command(name="list")
@click.option("--limit", "-l", default=20, help="Max papers to show")
def list_papers(limit: int) -> None:
    """List papers in the database."""
    engine = _get_engine()
    papers = engine.list_papers(limit=limit)

    if not papers:
        console.print("[yellow]No papers in database[/yellow]")
        return

    table = Table(title=f"Papers ({len(papers)})")
    table.add_column("ID", style="dim", max_width=8)
    table.add_column("Year", width=6)
    table.add_column("Title", max_width=60)
    table.add_column("Summary", max_width=10)

    for p in papers:
        paper_id = p.id[:8]
        year = str(p.year) if p.year else "-"
        has_summary = "yes" if p.ai_summary else "no"
        table.add_row(paper_id, year, p.title[:60], has_summary)

    console.print(table)


@main.command()
@click.argument("paper_id")
def show(paper_id: str) -> None:
    """Show details for a paper (use first 8 chars of ID)."""
    engine = _get_engine()

    # Support partial IDs
    papers = engine.list_papers(limit=1000)
    match = None
    for p in papers:
        if p.id.startswith(paper_id):
            match = p
            break

    if match is None:
        console.print(f"[red]Paper not found: {paper_id}[/red]")
        return

    paper = engine.get_paper(match.id)
    if paper is None:
        console.print(f"[red]Paper not found: {paper_id}[/red]")
        return

    console.print(f"\n[bold]{paper.title}[/bold]")
    console.print(f"ID:   {paper.id}")
    console.print(f"Year: {paper.year or 'unknown'}")
    console.print(f"DOI:  {paper.doi or 'none'}")

    if paper.authors:
        names = [a.name for a in paper.authors]
        console.print(f"Authors: {', '.join(names)}")

    if paper.abstract:
        console.print(f"\n[bold]Abstract:[/bold]\n{paper.abstract[:500]}")

    if paper.ai_summary:
        console.print(f"\n[bold]AI Summary:[/bold]\n{paper.ai_summary}")

    if paper.citing_refs:
        console.print(f"\n[bold]References ({len(paper.citing_refs)}):[/bold]")
        for ref in paper.citing_refs[:10]:
            year = f" ({ref.cited_year})" if ref.cited_year else ""
            console.print(f"  - {ref.cited_title}{year}")
        if len(paper.citing_refs) > 10:
            console.print(f"  ... and {len(paper.citing_refs) - 10} more")


@main.command()
@click.argument("query")
@click.option("--limit", "-l", default=20, help="Max results")
def search(query: str, limit: int) -> None:
    """Search papers (semantic when embeddings exist, else title match)."""
    engine = _get_engine()
    results = engine.search_papers(query, limit=limit)

    if not results:
        console.print(f"[yellow]No papers matching '{query}'[/yellow]")
        return

    for r in results:
        p = r["paper"]
        score = r["score"]
        year = f" ({p.year})" if p.year else ""
        score_str = f" [cyan]{score:.0%}[/cyan]" if score is not None else ""
        console.print(f"  [{p.id[:8]}] {p.title}{year}{score_str}")


@main.command()
@click.argument("paper_id")
def summarize(paper_id: str) -> None:
    """Generate AI summary for a paper."""
    engine = _get_engine()

    papers = engine.list_papers(limit=1000)
    match = None
    for p in papers:
        if p.id.startswith(paper_id):
            match = p
            break

    if match is None:
        console.print(f"[red]Paper not found: {paper_id}[/red]")
        return

    with console.status("Generating AI summary..."):
        paper = asyncio.run(engine.summarize_paper(match.id))

    console.print(f"\n[bold green]Summary for: {paper.title}[/bold green]")
    console.print(f"\n{paper.ai_summary}")

    if paper.ai_key_contributions:
        console.print("\n[bold]Key contributions:[/bold]")
        for c in paper.ai_key_contributions:
            console.print(f"  - {c}")


@main.command()
@click.argument("paper_id")
def tag(paper_id: str) -> None:
    """Generate AI tags for a paper."""
    engine = _get_engine()

    papers = engine.list_papers(limit=1000)
    match = None
    for p in papers:
        if p.id.startswith(paper_id):
            match = p
            break

    if match is None:
        console.print(f"[red]Paper not found: {paper_id}[/red]")
        return

    with console.status("Generating tags..."):
        tags = asyncio.run(engine.tag_paper(match.id))

    console.print(f"\n[bold green]Tags for: {match.title}[/bold green]")
    for t in tags:
        console.print(f"  - {t}")


@main.command(name="summarize-all")
def summarize_all() -> None:
    """Generate AI summaries for all papers that don't have one yet."""
    engine = _get_engine()
    total = engine.count_papers()
    console.print(f"Checking {total} papers for missing summaries...")

    result = asyncio.run(engine.summarize_all())
    done = result["done"]
    failed = result["failed"]

    for title in done:
        console.print(f"  [green]OK[/green] {title[:60]}")
    for title in failed:
        console.print(f"  [red]FAIL[/red] {title[:60]}")

    if not done and not failed:
        console.print("[yellow]All papers already have summaries[/yellow]")
    else:
        console.print(f"\nDone: {len(done)} summarized, {len(failed)} failed")


@main.command(name="tag-all")
def tag_all() -> None:
    """Generate AI tags for all papers that don't have any yet."""
    engine = _get_engine()
    total = engine.count_papers()
    console.print(f"Checking {total} papers for missing tags...")

    result = asyncio.run(engine.tag_all())
    done = result["done"]
    failed = result["failed"]

    for title in done:
        console.print(f"  [green]OK[/green] {title[:60]}")
    for title in failed:
        console.print(f"  [red]FAIL[/red] {title[:60]}")

    if not done and not failed:
        console.print("[yellow]All papers already have tags[/yellow]")
    else:
        console.print(f"\nDone: {len(done)} tagged, {len(failed)} failed")


@main.command(name="embed-all")
def embed_all() -> None:
    """Backfill embeddings for all existing papers."""
    engine = _get_engine()

    with console.status("Indexing embeddings for all papers..."):
        counts = engine.backfill_embeddings()

    console.print(
        f"[bold green]Done:[/bold green] {counts['indexed']} indexed, "
        f"{counts['failed']} failed"
    )


@main.command(name="find-refs")
@click.argument("text")
@click.option("--limit", "-l", default=5, help="Max references to return")
@click.option("--explain", is_flag=True, help="Include AI explanations")
def find_refs(text: str, limit: int, explain: bool) -> None:
    """Find papers that could support a claim or sentence."""
    engine = _get_engine()

    with console.status("Searching for references..."):
        results = asyncio.run(
            engine.find_references(text, limit=limit, explain=explain)
        )

    if not results:
        console.print("[yellow]No matching references found[/yellow]")
        return

    console.print(f"\n[bold]References for:[/bold] {text}\n")
    for r in results:
        p = r["paper"]
        score = r["score"]
        year = f" ({p.year})" if p.year else ""
        authors = ", ".join(a.name for a in p.authors) if p.authors else ""
        console.print(f"  [cyan]{score:.0%}[/cyan] {p.title}{year}")
        if authors:
            console.print(f"       {authors}")
        if r.get("explanation"):
            console.print(f"       [dim]{r['explanation']}[/dim]")
        console.print()


if __name__ == "__main__":
    main()
