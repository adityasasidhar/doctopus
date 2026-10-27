from __future__ import annotations

import os
import secrets
import tempfile
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from doctopus import __version__
from doctopus.core.chunk import Chunk
from doctopus.core.chunk import chunk as make_chunks
from doctopus.core.errors import DoctopusError, ExtractionFailed, InputRejected, UnsupportedFormat
from doctopus.core.gateway import Gateway

MAX_UPLOAD_MB = int(os.environ.get("DOCTOPUS_MAX_UPLOAD_MB", "50"))
TOKEN = os.environ.get("DOCTOPUS_API_TOKEN")  # unset = open (local dev); set for any public deployment
STATIC = Path(__file__).parent / "static"

app = FastAPI(title="Doctopus", version=__version__, description="Many arms. One API.")
gw = Gateway(max_bytes=MAX_UPLOAD_MB * 1024 * 1024)


def auth(authorization: str | None = Header(default=None)):
    if TOKEN and not (authorization and secrets.compare_digest(authorization, f"Bearer {TOKEN}")):
        raise HTTPException(401, {"error": "unauthorized", "message": "missing or invalid bearer token"})


@app.exception_handler(DoctopusError)
async def _err(_, e: DoctopusError):
    status = {InputRejected: 400, UnsupportedFormat: 415, ExtractionFailed: 422}.get(type(e), 500)
    return JSONResponse({"error": e.code, "message": str(e)}, status_code=status)


async def _spool(file: UploadFile) -> Path:
    """Stream the upload to disk (never fully in RAM), enforcing the size cap."""
    suffix = Path(file.filename or "upload").suffix
    fd, name = tempfile.mkstemp(suffix=suffix, prefix="doctopus_")
    size = 0
    with os.fdopen(fd, "wb") as out:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_UPLOAD_MB * 1024 * 1024:
                out.close()
                os.unlink(name)
                raise InputRejected(f"upload exceeds {MAX_UPLOAD_MB} MB")
            out.write(chunk)
    return Path(name)


@app.post("/v1/parse", dependencies=[Depends(auth)])
async def parse(
    file: UploadFile = File(...),
    backend: str | None = Form(None),  # None -> server default ($DOCTOPUS_BACKEND / serve --backend)
    mode: Literal["fast", "balanced", "accurate"] = Form("balanced"),
    fallback: bool | None = Form(None),  # None -> gateway policy (auto: one escalation; manual: none)
):
    p = await _spool(file)
    try:
        doc = await gw.parse(p, backend=backend, mode=mode, fallback=fallback)
    finally:
        p.unlink(missing_ok=True)
    doc.meta.filename = file.filename or doc.meta.filename  # report the user's name, not the temp name
    return doc


@app.post("/v1/chunk", dependencies=[Depends(auth)], response_model=list[Chunk])
async def chunk(
    file: UploadFile = File(...),
    backend: str | None = Form(None),  # None -> server default ($DOCTOPUS_BACKEND / serve --backend)
    mode: Literal["fast", "balanced", "accurate"] = Form("balanced"),
    max_chars: int = Form(1500, ge=100, le=20_000),
):
    doc = await parse(file, backend=backend, mode=mode, fallback=None)
    return make_chunks(doc, max_chars=max_chars)


@app.post("/v1/plan", dependencies=[Depends(auth)])
async def plan(file: UploadFile = File(...), mode: Literal["fast", "balanced", "accurate"] = Form("balanced"),
               backend: str | None = Form(None)):
    p = await _spool(file)
    try:
        return gw.plan(p, backend=backend, mode=mode)
    finally:
        p.unlink(missing_ok=True)


@app.get("/v1/backends", dependencies=[Depends(auth)])
def backends():
    return gw.list_backends()


@app.get("/v1/health")
def health():
    return {"status": "ok", "version": __version__, "default_backend": gw.default_backend,
            "backends_ready": [b.id for b in gw.list_backends() if b.available]}


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/logo.png", include_in_schema=False)
def logo():
    return FileResponse(STATIC / "logo.png", media_type="image/png")
