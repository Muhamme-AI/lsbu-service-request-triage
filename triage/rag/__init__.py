"""Load guidance, chunk it, and store embeddings in a local vector database."""

from .pipeline import ensure_index, index_stats, retrieve, retrieve_requests

__all__ = ["ensure_index", "index_stats", "retrieve", "retrieve_requests"]
