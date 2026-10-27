# MCP server

Doctopus ships a [Model Context Protocol](https://modelcontextprotocol.io/) server, so agents can parse, chunk and compare documents in a folder you choose.

```bash
doctopus mcp --root ./docs
```

The server runs over stdio. Paths may be relative to `--root` or absolute within it; paths and symlinks that resolve outside the root are rejected.

## Client configuration

=== "Installed command"

    ```json
    {
      "mcpServers": {
        "doctopus": {
          "command": "doctopus",
          "args": ["mcp", "--root", "/path/to/docs"]
        }
      }
    }
    ```

=== "uvx (no install)"

    ```json
    {
      "mcpServers": {
        "doctopus": {
          "command": "uvx",
          "args": ["--python", "3.12", "--from", "doctopus-ai", "doctopus", "mcp", "--root", "/path/to/docs"]
        }
      }
    }
    ```

=== "Source checkout"

    ```json
    {
      "mcpServers": {
        "doctopus": {
          "command": "uv",
          "args": ["--directory", "/path/to/doctopus", "run", "doctopus", "mcp", "--root", "/path/to/docs"]
        }
      }
    }
    ```

For Claude Code:

```bash
claude mcp add doctopus -- doctopus mcp --root /path/to/docs
```

Use `--backend` (or `DOCTOPUS_BACKEND`) to set the default engine for tool calls that do not name one.

## Tools

| Tool | What it does |
| --- | --- |
| `parse_document` | Returns Markdown, metadata, tables, and processing details. |
| `chunk_document` | Returns paged chunks for retrieval or dataset building. |
| `explain_routing` | Returns the routing decision for a file without extracting it. |
| `list_processing_backends` | Lists engines with availability and capabilities. |
| `compare_processors` | Runs every available engine with fallback disabled and reports per-engine results or failures. |

- `parse_document` caps Markdown at 60,000 characters by default (`max_chars`); `truncated` and `total_chars` describe the full length. Blocks are included only with `include_blocks=True`. It returns a subset of the canonical document, not its full JSON schema.
- `chunk_document` pages its results with `offset` and `limit` (default 50), plus `total`. Each call parses the file again.
- `parse_document`, `chunk_document` and `explain_routing` accept a `backend` argument.
