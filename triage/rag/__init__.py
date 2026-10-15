"""Load guidance, chunk it, and store embeddings in a local vector database."""

from .pipeline import ensure_index, retrieve

__all__ = ["ensure_index", "retrieve"]
