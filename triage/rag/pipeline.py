"""Load guidance, chunk it, embed it, store it, and retrieve the closest chunks.

Sources
-------
* ``knowledge/*.md``  - written guidance for reviewers.
* ``config/*.json``   - the live rules and acknowledgement templates, so the
  assistant quotes the same thresholds the engine uses.
* the open batch      - the requests the reviewer has loaded, indexed in
  memory per call so the assistant can find "the overdue access request".

The store is SQLite with one row per chunk. Vectors are TF-IDF over the
indexed vocabulary, L2-normalised, so retrieval is cosine similarity. There is
no network call and no model in this file.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..config import CONFIG_DIR, PROJECT_ROOT
from .embed import build_space, cosine, embed

KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge"
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "vectors.sqlite"
CHUNK_CHARS = 700
CHUNK_OVERLAP = 80
INDEX_VERSION = "tfidf-v5"
MIN_SCORE = 0.12

_lock = threading.Lock()


@dataclass(frozen=True)
class Chunk:
    source: str
    text: str
    score: float = 0.0
    kind: str = "guidance"


def chunk_text(text: str, *, size: int = CHUNK_CHARS, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks on paragraph boundaries."""
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    if not paragraphs:
        compact = " ".join(text.split())
        return [compact] if compact else []
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        piece = paragraph if len(paragraph) <= size else paragraph[:size]
        if current and len(current) + len(piece) + 1 > size:
            chunks.append(current)
            tail = current[-overlap:] if overlap else ""
            current = f"{tail} {piece}".strip()
        else:
            current = f"{current}\n\n{piece}".strip() if current else piece
    if current:
        chunks.append(current)
    return chunks


def source_files() -> list[Path]:
    guidance = sorted(KNOWLEDGE_DIR.glob("*.md"))
    config = [CONFIG_DIR / "rules.json", CONFIG_DIR / "acknowledgements.json"]
    return guidance + [path for path in config if path.exists()]


def _rules_to_chunks(rules: dict[str, Any]) -> list[str]:
    """One chunk per rule so a question about one category does not match every category."""
    chunks: list[str] = []
    for category in rules.get("categorisation", {}).get("categories", []):
        chunks.append(
            f"Categorisation rule for {category['name']}. {category.get('description', '')} "
            f"The rule-based category is {category['name']} when the summary contains strong keywords such as "
            f"{', '.join(category.get('strong', [])[:8])}, or weak keywords such as {', '.join(category.get('weak', [])[:6])}."
        )
    validation = rules.get("validation", {})
    chunks.append(
        "Validation rule. Required fields on every request: " + ", ".join(validation.get("required_fields", [])) + ". "
        f"Allowed priorities are {', '.join(validation.get('allowed_priorities', []))}. "
        f"Allowed statuses are {', '.join(validation.get('allowed_statuses', []))}. "
        f"A summary shorter than {validation.get('minimum_summary_length')} characters is too short to act on."
    )
    review = rules.get("review", {})
    chunks.append(
        f"Overdue rule. A request still {' or '.join(review.get('overdue_statuses', []))} after "
        f"{review.get('overdue_days')} days is overdue and needs a person. "
        f"A {' or '.join(review.get('attention_priorities', []))} priority request always needs a person."
    )
    return chunks


def _ack_to_chunks(config: dict[str, Any]) -> list[str]:
    targets = ", ".join(f"{k} priority {v}" for k, v in config.get("response_targets", {}).items() if k != "default")
    chunks = [f"Response target by priority. The response target is {targets}. These are working days."]
    chunks.append(f"Acknowledgement template used for every request:\n{config.get('template', '')}")
    for name, note in config.get("category_notes", {}).items():
        chunks.append(f"Acknowledgement note for a {name} request: {note}")
    if config.get("incomplete_note"):
        chunks.append(f"Acknowledgement note when information is missing: {config['incomplete_note']}")
    return chunks


def _read_chunks(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    if path.suffix != ".json":
        return chunk_text(text)
    data = json.loads(text)
    if path.name == "rules.json":
        return _rules_to_chunks(data)
    if path.name == "acknowledgements.json":
        return _ack_to_chunks(data)
    return chunk_text(json.dumps(data, indent=2))


def corpus_hash(files: list[Path] | None = None) -> str:
    digest = hashlib.sha256()
    digest.update(INDEX_VERSION.encode("utf-8"))
    for path in files if files is not None else source_files():
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY,
            source TEXT NOT NULL,
            text TEXT NOT NULL,
            embedding TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    return connection


def _set_meta(connection: sqlite3.Connection, key: str, value: str) -> None:
    connection.execute(
        "INSERT INTO meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )


def build_index(db_path: Path, files: list[Path] | None = None) -> int:
    """Replace the vector database with a fresh index. Returns the chunk count."""
    documents = files if files is not None else source_files()
    pieces = [(path.name, piece) for path in documents for piece in _read_chunks(path)]
    vocabulary, weights = build_space([text for _, text in pieces])
    rows = [(source, text, json.dumps(embed(text, vocabulary, weights))) for source, text in pieces]
    connection = _connect(db_path)
    try:
        connection.execute("DELETE FROM chunks")
        connection.executemany("INSERT INTO chunks (source, text, embedding) VALUES (?, ?, ?)", rows)
        _set_meta(connection, "corpus_hash", corpus_hash(documents))
        _set_meta(connection, "idf", json.dumps(weights))
        _set_meta(connection, "vocabulary", json.dumps(vocabulary))
        connection.commit()
    finally:
        connection.close()
    return len(rows)


def _stored_hash(db_path: Path) -> str | None:
    if not db_path.exists():
        return None
    connection = _connect(db_path)
    try:
        row = connection.execute("SELECT value FROM meta WHERE key = 'corpus_hash'").fetchone()
    finally:
        connection.close()
    return row[0] if row else None


def writable_db_path(preferred: Path | None = None) -> Path:
    """Use the project data folder, or /tmp when the deployment disk is read-only."""
    path = preferred or DEFAULT_DB_PATH
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        probe = path.parent / ".write-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return path
    except OSError:
        return Path("/tmp/triage-vectors.sqlite")


def ensure_index(db_path: Path | None = None) -> Path:
    """Build the index when it is missing or the source files have changed."""
    path = writable_db_path(db_path)
    with _lock:
        if _stored_hash(path) != corpus_hash():
            build_index(path)
    return path


def index_stats(db_path: Path | None = None) -> dict[str, Any]:
    path = ensure_index(db_path)
    connection = _connect(path)
    try:
        rows = connection.execute("SELECT source, COUNT(*) FROM chunks GROUP BY source ORDER BY source").fetchall()
        vocab_row = connection.execute("SELECT value FROM meta WHERE key = 'vocabulary'").fetchone()
    finally:
        connection.close()
    return {
        "path": str(path),
        "chunks": sum(count for _, count in rows),
        "sources": {source: count for source, count in rows},
        "vocabulary": len(json.loads(vocab_row[0])) if vocab_row else 0,
        "index_version": INDEX_VERSION,
    }


def _load_space(path: Path) -> tuple[dict[str, int], dict[str, float], list[tuple[str, str, str]]]:
    connection = _connect(path)
    try:
        idf_row = connection.execute("SELECT value FROM meta WHERE key = 'idf'").fetchone()
        vocabulary_row = connection.execute("SELECT value FROM meta WHERE key = 'vocabulary'").fetchone()
        stored = connection.execute("SELECT source, text, embedding FROM chunks").fetchall()
    finally:
        connection.close()
    vocabulary = json.loads(vocabulary_row[0]) if vocabulary_row else {}
    weights = json.loads(idf_row[0]) if idf_row else {}
    return vocabulary, weights, stored


def retrieve(query: str, *, db_path: Path | None = None, limit: int = 4, min_score: float = MIN_SCORE) -> list[Chunk]:
    """Best chunk per source, highest first, above the relevance floor."""
    path = ensure_index(db_path)
    vocabulary, weights, stored = _load_space(path)
    query_vector = embed(query, vocabulary, weights)
    best: dict[str, Chunk] = {}
    for source, text, raw_embedding in stored:
        score = cosine(query_vector, json.loads(raw_embedding))
        if score < min_score:
            continue
        current = best.get(source)
        if current is None or score > current.score:
            best[source] = Chunk(source, text, score, "guidance")
    ranked = sorted(best.values(), key=lambda item: item.score, reverse=True)
    return ranked[:limit]


def request_text(item: dict[str, Any]) -> str:
    """One searchable line per request from the open batch."""
    flags = item.get("flags") or []
    return " | ".join(
        [
            str(item.get("request_id") or "no reference"),
            str(item.get("category") or "uncategorised"),
            f"{item.get('priority') or 'unspecified'} priority",
            f"status {item.get('status') or 'unspecified'}",
            "flags " + (", ".join(str(flag) for flag in flags) if flags else "none"),
            str(item.get("summary") or ""),
        ]
    )


def retrieve_requests(query: str, requests: list[dict[str, Any]], *, limit: int = 5) -> list[Chunk]:
    """Rank the open batch against the question. In memory; the batch is never written to disk."""
    if not requests:
        return []
    texts = [request_text(item) for item in requests]
    vocabulary, weights = build_space(texts + [query])
    query_vector = embed(query, vocabulary, weights)
    scored: list[Chunk] = []
    for item, text in zip(requests, texts):
        score = cosine(query_vector, embed(text, vocabulary, weights))
        reference = str(item.get("request_id") or "")
        if reference and reference.lower() in query.lower():
            score += 1.0
        if score > 0:
            scored.append(Chunk(reference or "request", text, score, "request"))
    scored.sort(key=lambda item: item.score, reverse=True)
    return scored[:limit]
