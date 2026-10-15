from triage.rag.embed import build_space, cosine, embed
from triage.rag.pipeline import build_index, chunk_text, retrieve, source_files


def test_chunking_keeps_short_text_and_overlaps_long_text():
    assert chunk_text("  ") == []
    assert chunk_text("One paragraph about access.") == ["One paragraph about access."]
    long_text = "\n\n".join(f"Paragraph {index} " + ("word " * 40) for index in range(8))
    chunks = chunk_text(long_text, size=200, overlap=20)
    assert len(chunks) > 1
    assert all(len(chunk) <= 250 for chunk in chunks)


def test_embeddings_are_stable_and_related_text_scores_higher():
    documents = [
        "external collaborator information governance check before access",
        "timetable room booking export overnight",
    ]
    vocabulary, weights = build_space(documents)
    first = embed(documents[0], vocabulary, weights)
    assert embed(documents[0], vocabulary, weights) == first
    related = cosine(first, embed("grant external collaborator access after an information governance check", vocabulary, weights))
    unrelated = cosine(first, embed("timetable room booking export", vocabulary, weights))
    assert related > unrelated
    assert related > 0


def test_index_retrieves_the_guidance_that_matches_the_question(tmp_path):
    db = tmp_path / "vectors.sqlite"
    count = build_index(db, source_files())
    assert count >= 5
    access = retrieve("What should I do before granting access to an external collaborator?", db_path=db)
    assert access
    assert access[0].source == "access-and-permissions.md"
    assert "information-governance" in access[0].text
    email = retrieve("Draft a reply email and what response target applies to high priority", db_path=db)
    assert any(hit.source == "email-drafts.md" for hit in email)
    personal = retrieve("Can I put the requester email address and password in the reply?", db_path=db)
    assert "content-and-personal-data.md" in [hit.source for hit in personal[:3]]
