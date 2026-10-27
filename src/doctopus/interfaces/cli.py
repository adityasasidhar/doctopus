from __future__ import annotations

import asyncio
import json
import os
import sys
from enum import Enum
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table as RichTable

from doctopus.core.errors import DoctopusError
from doctopus.core.gateway import Gateway

app = typer.Typer(help="Doctopus 🐙  Many arms. One API.", no_args_is_help=True, add_completion=False)
backends_app = typer.Typer(help="Inspect available engines.", no_args_is_help=True)
app.add_typer(backends_app, name="backends")
err = Console(stderr=True, soft_wrap=True)  # logs never touch stdout
BACKEND_HELP = "auto | engine id (see `doctopus backends list`); default: $DOCTOPUS_BACKEND, else auto"


class Fmt(str, Enum):
    md = "md"
    json = "json"
    text = "text"


class Mode(str, Enum):
    fast = "fast"
    balanced = "balanced"
    accurate = "accurate"


def _fail(e: Exception, code: int):
    err.print(f"[red]error[/red] {getattr(e, 'code', 'error')}: {e}")
    raise typer.Exit(code)


@app.command()
def parse(
    file: Path = typer.Argument(..., help="Document to process"),
    backend: str | None = typer.Option(None, "--backend", "-b", help=BACKEND_HELP),
    mode: Mode = typer.Option(Mode.balanced, "--mode", "-m", help="fast | balanced | accurate"),
    fmt: Fmt = typer.Option(Fmt.md, "--format", "-f"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Write result here instead of stdout"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="No routing summary on stderr"),
    ocr: bool = typer.Option(False, "--ocr", help="Force OCR"),
    no_fallback: bool = typer.Option(False, "--no-fallback"),
):
    """Parse FILE into Markdown / text / canonical JSON."""
    try:
        doc = asyncio.run(Gateway().parse(file, backend=backend, mode=mode.value, ocr=ocr or None,
                                          fallback=False if no_fallback else None))
    except DoctopusError as e:
        _fail(e, 2)
    except Exception as e:  # unexpected
        _fail(e, 1)
    p = doc.processing
    if not quiet:
        d = p.decision
        err.print(f"🐙 [bold]{p.backend}[/bold] {p.elapsed_ms} ms · {doc.meta.page_count or '?'} pages · "
                  f"{len(doc.tables)} tables" + (f" · fell back from {p.fallback_from}" if p.fallback_from else ""))
        if d:
            for line in d.reasons:
                err.print(f"   [dim]• {line}[/dim]")
        for w in p.warnings:
            err.print(f"   [yellow]! {w}[/yellow]")
    out = {Fmt.md: doc.markdown, Fmt.text: doc.text, Fmt.json: doc.model_dump_json(indent=2)}[fmt]
    if output:
        output.write_text(out, encoding="utf-8")
        err.print(f"wrote {output}")
    else:
        sys.stdout.write(out if out.endswith("\n") else out + "\n")


@app.command()
def chunk(
    paths: list[Path] = typer.Argument(..., help="Files and/or directories (searched recursively)"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Write JSONL here instead of stdout"),
    max_chars: int = typer.Option(1500, "--max-chars", help="Target chunk size; tables are never split"),
    backend: str | None = typer.Option(None, "--backend", "-b", help=BACKEND_HELP),
    mode: Mode = typer.Option(Mode.balanced, "--mode", "-m", help="fast | balanced | accurate"),
):
    """Export layout-aware chunks as JSONL (one chunk per line) for RAG or dataset building."""
    from doctopus.core.chunk import chunk as make_chunks

    try:
        gw = Gateway()
    except DoctopusError as e:  # e.g. an unknown $DOCTOPUS_BACKEND
        _fail(e, 2)
    exts ={f for i in gw.list_backends() if i.available for f in i.formats}
    files = []
    for p in paths:
        if p.is_dir():
            files += sorted(f for f in p.rglob("*") if f.is_file() and f.suffix.lstrip(".").lower() in exts)
        else:
            files.append(p)
    if not files:
        _fail(typer.BadParameter("no supported documents found"), 2)

    async def run(sink):
        seen, n_chunks, failed = set(), 0, []
        for f in files:
            try:
                doc = await gw.parse(f, backend=backend, mode=mode.value)
            except Exception as e:  # one bad file must not sink a batch
                failed.append(f)
                err.print(f"[red]✗[/red] {f}: {e}")
                continue
            if doc.meta.content_hash in seen:
                err.print(f"[dim]= {f}: duplicate content, skipped[/dim]")
                continue
            seen.add(doc.meta.content_hash)
            cs = make_chunks(doc, max_chars=max_chars)
            for c in cs:
                sink.write(c.model_dump_json() + "\n")
            n_chunks += len(cs)
            err.print(f"🐙 {f} → {len(cs)} chunks [dim]({doc.processing.backend}, {doc.processing.elapsed_ms} ms)[/dim]")
        err.print(f"[bold]{n_chunks} chunks[/bold] from {len(seen)} documents"
                  + (f", [red]{len(failed)} failed[/red]" if failed else ""))
        return failed

    if output:
        with output.open("w", encoding="utf-8") as fh:
            failed = asyncio.run(run(fh))
        err.print(f"wrote {output}")
    else:
        failed = asyncio.run(run(sys.stdout))
    if failed:
        raise typer.Exit(2)


@app.command()
def plan(
    file: Path,
    mode: Mode = typer.Option(Mode.balanced, "--mode", "-m"),
    backend: str | None = typer.Option(None, "--backend", "-b", help=BACKEND_HELP),
):
    """Show which engine the router would pick, and why (no extraction)."""
    try:
        d = Gateway().plan(file, backend=backend, mode=mode.value)
    except DoctopusError as e:
        _fail(e, 2)
    typer.echo(d.model_dump_json(indent=2))


@backends_app.command("list")
def backends_list(as_json: bool = typer.Option(False, "--json")):
    infos = Gateway().list_backends()
    if as_json:
        typer.echo(json.dumps([i.model_dump() for i in infos], indent=2))
        return
    t = RichTable(title="Doctopus backends")
    for c in ("id", "version", "weight", "runs", "status", "licence"):
        t.add_column(c)
    for i in infos:
        t.add_row(i.id, i.version or "-", i.weight + (f" ({i.ram_mb / 1000:.0f} GB)" if i.ram_mb else ""), i.runtime,
                  "[green]ready[/green]" if i.available else f"[red]{i.reason_unavailable}[/red]",
                  (i.licence or "?").split(";")[0])
    Console().print(t)


def _set_default_backend(backend: str | None):
    """Validate, then hand the choice to the server process via the env var the Gateway reads."""
    if backend:
        try:
            Gateway(default_backend=backend)
        except DoctopusError as e:
            _fail(e, 2)
        os.environ["DOCTOPUS_BACKEND"] = backend


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000,
          backend: str | None = typer.Option(None, "--backend", "-b", help="Default engine for requests that "
                                             "do not name one; " + BACKEND_HELP)):
    """Start the REST API + demo UI."""
    import uvicorn
    _set_default_backend(backend)
    uvicorn.run("doctopus.interfaces.api:app", host=host, port=port, log_level="warning")


@app.command()
def mcp(root: Path = typer.Option(Path.cwd(), "--root", help="Only files under this directory are readable"),
        backend: str | None = typer.Option(None, "--backend", "-b", help="Default engine for tool calls that "
                                           "do not name one; " + BACKEND_HELP)):
    """Run the MCP server over stdio."""
    from doctopus.interfaces.mcp_server import run_stdio
    _set_default_backend(backend)
    run_stdio(root)


if __name__ == "__main__":
    app()
