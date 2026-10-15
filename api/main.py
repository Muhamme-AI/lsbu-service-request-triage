"""HTTP API for the service-request triage prototype.

Run locally with::

    uvicorn api.main:app --reload

Endpoints (all JSON):

* ``GET  /api/health``                 - liveness + whether the optional AI step is configured
* ``GET  /api/rules``                  - the rules and acknowledgement templates (for the "Rules" tab)
* ``GET  /api/sample?dataset=sample``  - triage one of the bundled synthetic data sets
* ``POST /api/triage``                 - multipart CSV upload -> triage results
* ``POST /api/acknowledgement/ai``     - re-draft one acknowledgement with the AI provider (if configured)

If ``frontend/dist`` exists (``npm run build``) it is served at ``/`` so the
demo runs from a single process.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from triage import __version__
from triage.ai import AIConfigError, AISettings, describe_chain, provider_chain
from triage.config import PROJECT_ROOT, load_ack_config, load_dotenv, load_rules
from triage.loader import LoaderError
from triage.assistant import answer
from triage.models import Request
from triage.pipeline import TriageRun, apply_ai, run_from_text, triage_requests
from triage.rag import ensure_index, index_stats
from triage.report import acknowledgements_markdown, run_to_dict, summary_markdown

DATASETS = {
    "sample": PROJECT_ROOT / "data" / "requests.csv",
    "edge-cases": PROJECT_ROOT / "data" / "requests_edge_cases.csv",
}
MAX_UPLOAD_BYTES = 2 * 1024 * 1024
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"

load_dotenv()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Build the retrieval index once at startup so the first question is not slow."""
    ensure_index()
    yield


app = FastAPI(
    title="Service Request Triage API",
    version=__version__,
    description="Validates, categorises, acknowledges and flags service requests from a CSV file.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def ai_settings_or_none() -> tuple[list[AISettings] | None, str | None]:
    """Return (provider chain, problem). Never raises: the API must stay up without AI."""
    try:
        return provider_chain(), None
    except AIConfigError as exc:
        return None, str(exc)


def parse_as_of(value: str | None) -> date | None:
    if not value:
        return None
    if value.strip().lower() == "today":
        return date.today()
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="as_of must be YYYY-MM-DD or 'today'") from exc


def serialise(run: TriageRun) -> dict[str, Any]:
    payload = run_to_dict(run)
    payload["markdown"] = {
        "summary": summary_markdown(run),
        "acknowledgements": acknowledgements_markdown(run),
    }
    return payload


@app.get("/api/health")
def health() -> dict[str, Any]:
    settings, problem = ai_settings_or_none()
    return {
        "status": "ok",
        "version": __version__,
        "ai_configured": settings is not None,
        "ai_provider": settings[0].describe() if settings else None,
        "ai_fallbacks": [item.describe() for item in settings[1:]] if settings else [],
        "ai_chain": describe_chain(settings) if settings else None,
        "ai_problem": problem,
    }


@app.get("/api/rules")
def rules() -> dict[str, Any]:
    return {"rules": load_rules(), "acknowledgements": load_ack_config()}


@app.get("/api/sample")
def sample(
    dataset: str = Query("sample", pattern="^(sample|edge-cases)$"),
    as_of: str | None = Query(None, description="YYYY-MM-DD or 'today'; default = latest submission date in the batch"),
    use_ai: bool = Query(False, description="refine acknowledgements with the configured AI provider"),
) -> dict[str, Any]:
    path = DATASETS[dataset]
    settings = ai_settings_or_none()[0] if use_ai else None
    text = path.read_text(encoding="utf-8-sig")
    return serialise(run_from_text(text, path.name, as_of=parse_as_of(as_of), ai_settings=settings))


@app.post("/api/triage")
async def triage(
    file: UploadFile = File(..., description="CSV file with one request per row"),
    as_of: str | None = Query(None),
    use_ai: bool = Query(False),
) -> dict[str, Any]:
    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File is larger than 2 MB")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = raw.decode("cp1252")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=400, detail="File is not readable as UTF-8 or Windows-1252 text") from exc
    settings = ai_settings_or_none()[0] if use_ai else None
    try:
        result = run_from_text(text, file.filename or "upload.csv", as_of=parse_as_of(as_of), ai_settings=settings)
    except LoaderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return serialise(result)


class RequestIn(BaseModel):
    row_number: int = 2
    request_id: str = ""
    submitted_date: str = ""
    requester_role: str = ""
    request_type: str = ""
    request_summary: str = ""
    priority: str = ""
    channel: str = ""
    status: str = ""


class AIDraftIn(BaseModel):
    request: RequestIn
    as_of: str | None = Field(None, description="YYYY-MM-DD or 'today'")


class ChatTurn(BaseModel):
    role: str
    content: str = Field("", max_length=4000)


class BatchItem(BaseModel):
    request_id: str = ""
    category: str = ""
    priority: str = ""
    status: str = ""
    summary: str = Field("", max_length=2000)
    flags: list[str] = []


class AssistantIn(BaseModel):
    question: str = Field("", max_length=4000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=40)
    requests: list[BatchItem] = Field(default_factory=list, max_length=500)


@app.post("/api/assistant")
def assistant(body: AssistantIn) -> dict[str, Any]:
    """Answer a reviewer question from the guidance index and the open batch.

    The batch is held in memory for this call only. Nothing is sent or changed.
    """
    settings, _problem = ai_settings_or_none()
    history = [
        {"role": turn.role, "content": turn.content}
        for turn in body.history
        if turn.role in {"user", "assistant"} and turn.content.strip()
    ]
    reply = answer(
        body.question,
        history=history,
        requests=[item.model_dump() for item in body.requests],
        settings=settings,
    )
    return {
        "reply": reply.text,
        "sources": reply.sources,
        "refused": reply.refused,
        "reason": reply.reason,
        "model": reply.model,
        "matched_requests": reply.matched_requests,
    }


@app.get("/api/assistant/index")
def assistant_index() -> dict[str, Any]:
    """What the retrieval index contains: file names, chunk counts, vocabulary size."""
    return index_stats()


@app.post("/api/acknowledgement/ai")
def acknowledgement_ai(body: AIDraftIn) -> dict[str, Any]:
    """Draft one acknowledgement with the AI provider; falls back to the template."""
    settings, problem = ai_settings_or_none()
    rules_cfg = load_rules()
    ack_cfg = load_ack_config()
    request = Request(**body.request.model_dump())
    as_of = parse_as_of(body.as_of) or date.today()
    result = triage_requests([request], rules_cfg, ack_cfg, as_of)[0]
    if settings is None:
        note = problem or "AI drafting is not configured (set TRIAGE_AI_PROVIDER in .env); template used"
        return {"ai_available": False, "acknowledgement": result.acknowledgement, "ack_source": "template", "ai_note": note}
    apply_ai(result, ack_cfg, settings)
    return {
        "ai_available": True,
        "acknowledgement": result.acknowledgement,
        "ack_source": result.ack_source,
        "ai_note": result.ai_note,
    }


if FRONTEND_DIST.exists():  # pragma: no cover - depends on a prior npm build
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
