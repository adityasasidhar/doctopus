# Command line

Installing `doctopus-ai` puts a `doctopus` command on your `PATH`. Run `doctopus --help`, or `--help` on any subcommand, to see its options.

```bash
# Markdown goes to stdout; the routing summary goes to stderr
doctopus parse paper.pdf

# Save the canonical JSON result
doctopus parse paper.pdf --format json --output result.json

# Choose an engine explicitly
doctopus parse report.docx --backend docling
doctopus parse scan.pdf --backend paddleocr

# Inspect routing or available engines
doctopus plan paper.pdf --mode accurate
doctopus backends list

# Export layout-aware chunks from files or folders as JSONL
doctopus chunk ./corpus --output corpus.jsonl
```

## `doctopus parse`

Parse one file into Markdown, plain text, or the canonical JSON [`Document`](../concepts/output.md).

```bash
doctopus parse FILE [OPTIONS]
```

| Option | Default | Description |
| --- | --- | --- |
| `--backend`, `-b` | `$DOCTOPUS_BACKEND`, else `auto` | `auto` or an engine id from `doctopus backends list` |
| `--mode`, `-m` | `balanced` | `fast`, `balanced` or `accurate` |
| `--format`, `-f` | `md` | `md`, `text` or `json` |
| `--output`, `-o` | stdout | Write the result to this file |
| `--quiet`, `-q` | off | Do not print the routing summary on stderr |
| `--ocr` | off | Request forced OCR where the engine supports it |
| `--no-fallback` | off | Never try an alternative engine |

## `doctopus chunk`

Parse files and directories (searched recursively) and write [chunks](../concepts/chunking.md) as JSONL.

```bash
doctopus chunk PATHS... [OPTIONS]
```

| Option | Default | Description |
| --- | --- | --- |
| `--output`, `-o` | stdout | Write JSONL to this file |
| `--max-chars` | `1500` | Target chunk size; tables are never split |
| `--backend`, `-b` | `$DOCTOPUS_BACKEND`, else `auto` | Engine for every file |
| `--mode`, `-m` | `balanced` | `fast`, `balanced` or `accurate` |

Directories are searched for extensions supported by the available engines. A file that fails is reported and the run continues; the exit code is `2` if any file failed.

## `doctopus plan`

Show the routing decision for a file without extracting it.

```bash
doctopus plan FILE [--mode MODE] [--backend ENGINE]
```

## `doctopus backends list`

List every engine with its availability, supported extensions, capabilities, and the reason an engine is unavailable. Add `--json` for machine-readable output.

## `doctopus serve`

Start the [REST API and demo UI](rest-api.md).

| Option | Default | Description |
| --- | --- | --- |
| `--host` | `127.0.0.1` | Interface to bind |
| `--port` | `8000` | Port to listen on |
| `--backend`, `-b` | `$DOCTOPUS_BACKEND`, else `auto` | Default engine for requests that do not name one |

## `doctopus mcp`

Start the [MCP server](mcp.md) over stdio.

| Option | Default | Description |
| --- | --- | --- |
| `--root` | current directory | Only files under this directory are readable |
| `--backend`, `-b` | `$DOCTOPUS_BACKEND`, else `auto` | Default engine for tool calls that do not name one |

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Success |
| `1` | Unexpected error |
| `2` | Doctopus error, such as an unsupported format or an unavailable engine; for `chunk`, at least one file failed |
