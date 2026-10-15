"""TF-IDF embeddings over the indexed vocabulary.

There is no hashing, so a rare word such as "password" or "reminder" only
moves the documents that actually contain it. Vectors are L2-normalised so
retrieval is cosine similarity.
"""

from __future__ import annotations

import math
import re


def tokens(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return words + [f"{words[i]}_{words[i + 1]}" for i in range(len(words) - 1)]


def build_space(chunks: list[str]) -> tuple[dict[str, int], dict[str, float]]:
    document_frequency: dict[str, int] = {}
    for text in chunks:
        for token in set(tokens(text)):
            document_frequency[token] = document_frequency.get(token, 0) + 1
    vocabulary = {token: index for index, token in enumerate(sorted(document_frequency))}
    count = max(len(chunks), 1)
    idf = {token: math.log((count + 1) / (freq + 1)) + 1 for token, freq in document_frequency.items()}
    return vocabulary, idf


def embed(text: str, vocabulary: dict[str, int], idf: dict[str, float]) -> list[float]:
    vector = [0.0] * max(len(vocabulary), 1)
    counts: dict[str, int] = {}
    for token in tokens(text):
        if token in vocabulary:
            counts[token] = counts.get(token, 0) + 1
    for token, count in counts.items():
        vector[vocabulary[token]] = (1.0 + math.log(count)) * idf[token]
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))
