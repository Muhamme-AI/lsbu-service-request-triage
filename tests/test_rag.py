from triage.rag.embed import build_space, cosine, embed, tokens
from triage.rag.pipeline import (
    build_index,
    chunk_text,
    corpus_hash,
    ensure_index,
    index_stats,
    retrieve,
    retrieve_requests,
    source_files,
)


def test_chunking_keeps_short_text_and_overlaps_long_text():
    assert chunk_text("  ") == []
    assert chunk_text("One paragraph about access.") == ["One paragraph about access."]
    long_text = "\n\n".join(f"Paragraph {index} " + ("word " * 40) for index in range(8))
    chunks = chunk_text(long_text, size=200, overlap=20)
    assert len(chunks) > 1
    assert all(len(chunk) <= 250 for chunk in chunks)
    # Overlap carries the tail of one chunk into the start of the next.
    assert chunks[0][-20:].strip().split()[-1] in chunks[1]


def test_tokens_include_word_pairs_so_phrases_match():
    assert "external_collaborator" in tokens("External collaborator access")
    assert tokens("") == []


def test_embeddings_are_stable_and_related_text_scores_higher():
    documents = [
        "external collaborator information governance check before access",
        "timetable room booking export overnight",
    ]
    vocabulary, weights = build_space(documents)
    first = embed(documents[0], vocabulary, weights)
    assert embed(documents[0], vocabulary, weights) == first
    assert abs(sum(value * value for value in first) - 1.0) < 1e-9  # unit length
    related = cosine(first, embed("grant external collaborator access after an information governance check", vocabulary, weights))
    unrelated = cosine(first, embed("timetable room booking export", vocabulary, weights))
    assert related > unrelated > 0 or (related > 0 and unrelated == 0)


def test_source_files_include_guidance_and_live_config():
    names = [path.name for path in source_files()]
    assert "access-and-permissions.md" in names
    assert "rules.json" in names and "acknowledgements.json" in names


def test_index_retrieves_the_guidance_that_matches_the_question(tmp_path):
    db = tmp_path / "vectors.sqlite"
    count = build_index(db, source_files())
    assert count >= 15
    access = retrieve("What should I do before granting access to an external collaborator?", db_path=db)
    assert access and access[0].source == "access-and-permissions.md"
    assert "information-governance" in access[0].text
    email = retrieve("Draft a reply email and what response target applies to high priority", db_path=db)
    assert any(hit.source == "email-drafts.md" for hit in email)
    personal = retrieve("Can I put the requester email address and password in the reply?", db_path=db)
    assert "content-and-personal-data.md" in [hit.source for hit in personal[:3]]
    rules = retrieve("What are the strong keywords for System Integration?", db_path=db)
    assert rules and rules[0].source == "rules.json" and "System Integration" in rules[0].text


def test_one_best_chunk_per_source_and_a_relevance_floor(tmp_path):
    db = tmp_path / "vectors.sqlite"
    build_index(db, source_files())
    hits = retrieve("external collaborator access", db_path=db, limit=10)
    sources = [hit.source for hit in hits]
    assert len(sources) == len(set(sources))
    assert all(hit.score >= 0.12 for hit in hits)
    assert retrieve("What's the weather like in London today?", db_path=db) == []
    assert retrieve("", db_path=db) == []


def test_ensure_index_rebuilds_only_when_sources_change(tmp_path, monkeypatch):
    db = tmp_path / "vectors.sqlite"
    first = ensure_index(db)
    assert first == db and db.exists()
    before = db.stat().st_mtime_ns
    ensure_index(db)
    assert db.stat().st_mtime_ns == before  # unchanged corpus, no rebuild
    monkeypatch.setattr("triage.rag.pipeline.corpus_hash", lambda files=None: "different")
    ensure_index(db)
    assert db.stat().st_mtime_ns >= before


def test_corpus_hash_changes_with_content(tmp_path):
    a = tmp_path / "a.md"
    a.write_text("alpha", encoding="utf-8")
    one = corpus_hash([a])
    a.write_text("beta", encoding="utf-8")
    assert corpus_hash([a]) != one


def test_index_stats_report_every_source(tmp_path):
    db = tmp_path / "vectors.sqlite"
    build_index(db, source_files())
    stats = index_stats(db)
    assert stats["chunks"] >= 15
    assert set(stats["sources"]) >= {"rules.json", "acknowledgements.json", "email-drafts.md"}
    assert stats["vocabulary"] > 100


BATCH = [
    {"request_id": "REQ-001", "category": "Access & Permissions", "priority": "Medium", "status": "New", "summary": "Request access to the student enquiries dashboard.", "flags": ["OVERDUE"]},
    {"request_id": "REQ-002", "category": "Process Automation", "priority": "High", "status": "In Review", "summary": "Automate the transfer of approved course changes.", "flags": ["HIGH_PRIORITY"]},
    {"request_id": "REQ-007", "category": "Access & Permissions", "priority": "Medium", "status": "Assigned", "summary": "Set up controlled access for external collaborators.", "flags": ["EXTERNAL_ACCESS"]},
]


def test_retrieve_requests_finds_the_right_row_in_the_batch():
    hits = retrieve_requests("Which request is about external collaborators?", BATCH)
    assert hits and hits[0].source == "REQ-007" and hits[0].kind == "request"
    overdue = retrieve_requests("what is overdue", BATCH)
    assert overdue and overdue[0].source == "REQ-001"
    assert retrieve_requests("anything", []) == []


def test_a_quoted_reference_outranks_similar_text():
    hits = retrieve_requests("Draft a reply for REQ-002", BATCH)
    assert hits[0].source == "REQ-002"
