# Python API

Generated from the source. For a guided introduction, see [Python usage](../usage/python.md).

## Top-level helpers

::: doctopus.parse

::: doctopus.chunk

::: doctopus.plan

::: doctopus.core.gateway.Gateway
    options:
      heading_level: 2
      members:
        - parse
        - plan
        - list_backends

## Document schema

::: doctopus.core.models
    options:
      show_root_heading: false
      show_root_toc_entry: false
      members:
        - Document
        - DocMeta
        - Block
        - Table
        - Page
        - Bbox
        - Processing
        - Decision
        - BackendInfo
        - SCHEMA_VERSION

## Chunks

::: doctopus.core.chunk
    options:
      show_root_heading: false
      show_root_toc_entry: false
      members:
        - chunk
        - Chunk
        - ChunkSource

## Errors

Every error carries a stable `code`, which the REST API and MCP tools return in their error payloads.

::: doctopus.core.errors
    options:
      show_root_heading: false
      show_root_toc_entry: false

## Backend protocol

Adapters implement this protocol and return a `RawResult`, which the gateway wraps into a `Document`.

::: doctopus.backends.base
    options:
      show_root_heading: false
      show_root_toc_entry: false
      members:
        - Backend
        - RawResult
