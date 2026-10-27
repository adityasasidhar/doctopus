# Deployment

## Docker Compose

Build and start the default Xberg image from a checkout of the repository:

```bash
docker compose -f deploy/docker-compose.yml up --build
```

The Compose service publishes port 8000 and sets a 512 MiB memory limit. This is the bundled base configuration, not a guarantee that every workload fits; heavy engines need more memory. Its volume preserves `/data`, with `XBERG_CACHE_DIR=/data/xberg`; other engines' model caches are not persisted by that volume unless you configure them there.

## Images with optional engines

```bash
docker build -f deploy/Dockerfile --build-arg EXTRA=docling -t doctopus:standard .
```

The `EXTRA` build argument installs one optional extra. Sidecar tools (Marker, MinerU) and an Ollama server are not included.

Compose defines one service. To use Docling through Compose, set `build.args.EXTRA: docling` and raise `mem_limit` in `deploy/docker-compose.yml`; building the separate `doctopus:standard` tag alone does not change the Compose service.

## Without Docker

```bash
pip install "doctopus-ai[docling]"
DOCTOPUS_API_TOKEN=change-me doctopus serve --host 0.0.0.0 --port 8000
```

## Configuration

The local `serve` command binds to `127.0.0.1` by default; the container serves on `0.0.0.0`. Compose forwards `DOCTOPUS_API_TOKEN` from the host and sets `DOCTOPUS_MAX_UPLOAD_MB` to 50. Add `DOCTOPUS_BACKEND`, `DOCTOPUS_HEAVY_ORDER`, or other settings to the Compose environment explicitly if needed. API settings are read when the server starts.

Uploaded documents are streamed to temporary files and removed after processing.

See [Configuration](reference/configuration.md) for every environment variable.

!!! warning "Exposing the API"
    Set `DOCTOPUS_API_TOKEN` whenever the server is reachable by anyone else. The health endpoint, demo page and API documentation stay public even when a token is set.
