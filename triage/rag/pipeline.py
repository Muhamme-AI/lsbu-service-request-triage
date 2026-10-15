"""Load guidance files, chunk them, and retrieve the closest chunks."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path

from ..config import PROJECT_ROOT
from .embed import build_space, cosine, embed

KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge"
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "vectors.sqlite"
CHUNK_CHARS = 2000
CHUNK_OVERLAP = 80
INDEX_VERSION = "tfidf-v2"

_lock = threading.Lock()


@dataclass(frozen=True)
class Chunk:
    source: str
    text: str
    score: float = 0.0


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
    return sorted(KNOWLEDGE_DIR.glob("*.md"))


def _read_source(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        return f"{path.name}\n{json.dumps(json.loads(text), indent=2)}"
    return text


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


def build_index(db_path: Path, files: list[Path] | None = None) -> int:
    """Replace the vector database with a fresh index. Returns the chunk count."""
    documents = files if files is not None else source_files()
    pieces = [(path.name, piece) for path in documents for piece in chunk_text(_read_source(path))]
    vocabulary, weights = build_space([text for _, text in pieces])
    rows = [(source, text, json.dumps(embed(text, vocabulary, weights))) for source, text in pieces]
    connection = _connect(db_path)
    try:
        connection.execute("DELETE FROM chunks")
        connection.executemany("INSERT INTO chunks (source, text, embedding) VALUES (?, ?, ?)", rows)
        connection.execute(
            "INSERT INTO meta (key, value) VALUES ('corpus_hash', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (corpus_hash(documents),),
        )
        connection.execute(
            "INSERT INTO meta (key, value) VALUES ('idf', ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (json.dumps(weights),),
        )
        connection.execute(
            "INSERT INTO meta (key, value) VALUES ('vocabulary', ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (json.dumps(vocabulary),),
        )
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
    """Build the index when it is missing or the guidance files have changed."""
    path = writable_db_path(db_path)
    with _lock:
        if _stored_hash(path) != corpus_hash():
            build_index(path)
    return path


def retrieve(query: str, *, db_path: Path | None = None, limit: int = 4) -> list[Chunk]:
    path = ensure_index(db_path)
    connection = _connect(path)
    try:
        idf_row = connection.execute("SELECT value FROM meta WHERE key = 'idf'").fetchone()
        vocabulary_row = connection.execute("SELECT value FROM meta WHERE key = 'vocabulary'").fetchone()
    finally:
        connection.close()
    vocabulary = json.loads(vocabulary_row[0]) if vocabulary_row else {}
    weights = json.loads(idf_row[0]) if idf_row else {}
    query_vector = embed(query, vocabulary, weights)
    connection = _connect(path)
    try:
        stored = connection.execute("SELECT source, text, embedding FROM chunks").fetchall()
    finally:
        connection.close()
    scored: list[Chunk] = []
    for source, text, raw_embedding in stored:
        score = cosine(query_vector, json.loads(raw_embedding))
        if score > 0:
            scored.append(Chunk(source, text, score))
    best: dict[str, Chunk] = {}
    for item in scored:
        current = best.get(item.source)
        if current is None or item.score > current.score:
            best[item.source] = item
    ranked = sorted(best.values(), key=lambda item: item.score, reverse=True)
    return ranked[:limit]
