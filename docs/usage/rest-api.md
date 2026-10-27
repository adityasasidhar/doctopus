# REST API & demo UI

```bash
doctopus serve --port 8000
```

Open [localhost:8000](http://localhost:8000) for the drag-and-drop demo, or send a document to the API:

```bash
curl -F file=@paper.pdf -F mode=balanced http://localhost:8000/v1/parse
```

Interactive OpenAPI documentation is served at [`/docs`](http://localhost:8000/docs).

## Endpoints

| Endpoint | Request / response |
| --- | --- |
| `POST /v1/parse` | Multipart `file`, optional `backend`, `mode`, `fallback`; returns a [`Document`](../concepts/output.md) as JSON |
| `POST /v1/chunk` | Multipart `file`, optional `backend`, `mode`, `max_chars` (100–20,000; default 1500); returns a JSON array of [chunks](../concepts/chunking.md) |
| `POST /v1/plan` | Multipart `file`, optional `backend`, `mode`; returns a routing decision without extraction |
| `GET /v1/backends` | Engine availability, formats, capabilities, and metadata |
| `GET /v1/health` | Status, version, deployment default, and ready engine IDs; no extraction check |

The three processing modes are `fast`, `balanced` (default) and `accurate`. A request without `backend` uses the server default (`doctopus serve --backend`, else `$DOCTOPUS_BACKEND`, else `auto`). REST does not currently expose an `ocr` field.

Uploads are limited to 50 MiB by default (`DOCTOPUS_MAX_UPLOAD_MB`). Uploaded documents are streamed to temporary files and removed after processing.

## Examples

=== "curl"

    ```bash
    curl -F file=@scan.pdf -F backend=docling http://localhost:8000/v1/parse
    curl -F file=@paper.pdf -F max_chars=1000 http://localhost:8000/v1/chunk
    curl -F file=@paper.pdf -F mode=accurate http://localhost:8000/v1/plan
    ```

=== "Python (httpx)"

    ```python
    import httpx

    with open("paper.pdf", "rb") as f:
        r = httpx.post(
            "http://localhost:8000/v1/parse",
            files={"file": f},
            data={"mode": "balanced"},
            timeout=300,
        )
    r.raise_for_status()
    print(r.json()["markdown"])
    ```

## Authentication

When `DOCTOPUS_API_TOKEN` is set, the parse, chunk, plan, and backends endpoints require a bearer token:

```bash
curl -H "Authorization: Bearer $DOCTOPUS_API_TOKEN" \
  -F file=@paper.pdf -F backend=xberg http://localhost:8000/v1/parse
```

The health endpoint, demo page, and API documentation remain public.

!!! warning
    The bundled demo does not send authorization headers, so it cannot process files against a token-protected API without an authentication-aware proxy or UI changes.

## Binding

`doctopus serve` binds to `127.0.0.1` by default. Pass `--host 0.0.0.0` to accept remote connections, and set `DOCTOPUS_API_TOKEN` when you do. The Docker image serves on `0.0.0.0`. See [Deployment](../deployment.md).
