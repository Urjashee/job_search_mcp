from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import re


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9\s]+", " ", text.lower()).strip()


def _tokens(text: str) -> list[str]:
    return [token for token in _normalize(text).split() if token]


@dataclass(slots=True)
class TextEmbedder:
    dimensions: int = 128

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in _tokens(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = digest[0] % self.dimensions
            sign = 1.0 if digest[1] % 2 == 0 else -1.0
            weight = 1.0 + (digest[2] / 255.0)
            vector[index] += sign * weight
        return vector


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0

    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def vector_to_text(vector: list[float]) -> str:
    return ",".join(f"{value:.8f}" for value in vector)


def text_to_vector(value: str, dimensions: int = 128) -> list[float]:
    parts = [part for part in value.split(",") if part]
    vector = [0.0] * dimensions
    for index, part in enumerate(parts[:dimensions]):
        try:
            vector[index] = float(part)
        except ValueError:
            vector[index] = 0.0
    return vector
