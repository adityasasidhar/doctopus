# Lite (default):   docker build -f deploy/Dockerfile -t doctopus:lite .
# Standard (+Docling, ~6 GB): docker build -f deploy/Dockerfile --build-arg EXTRA=docling -t doctopus:standard .
FROM python:3.12-slim
ENV UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
ARG EXTRA=""
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN --mount=from=ghcr.io/astral-sh/uv:0.13.1,source=/uv,target=/usr/local/bin/uv uv sync --locked --no-dev --no-cache --compile-bytecode ${EXTRA:+--extra $EXTRA} \
 && useradd -m app && mkdir -p /data && chown app /data
USER app
ENV XBERG_CACHE_DIR=/data/xberg DOCTOPUS_MAX_UPLOAD_MB=50 PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/v1/health')"
CMD ["doctopus", "serve", "--host", "0.0.0.0", "--port", "8000"]
