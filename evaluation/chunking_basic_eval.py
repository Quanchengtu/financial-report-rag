"""Basic chunking evaluation utilities for financial-report RAG.

This file is intentionally separate from the existing evaluation/ folder so the
chunking settings can be checked quickly before running retrieval or LLM evals.
It measures simple, deterministic signals that explain whether a chunking setup
is reasonable: number of chunks, average chunk length, size utilization,
repeated text from overlap, and sentence-boundary readability.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from backend.app.services.text_chunker import chunk_text


@dataclass(frozen=True)
class ChunkingMetrics:
    """Small set of metrics for comparing chunk_size / overlap settings."""

    chunk_size: int
    overlap: int
    chunk_count: int
    average_chunk_length: float
    max_chunk_length: int
    size_utilization: float
    repeated_character_ratio: float
    sentence_boundary_ratio: float


def _count_repeated_boundary_chars(chunks: list[str], overlap: int) -> int:
    """Estimate duplicated characters created by overlap between adjacent chunks."""
    if overlap <= 0 or len(chunks) < 2:
        return 0

    repeated_chars = 0
    for previous_chunk, current_chunk in zip(chunks, chunks[1:]):
        previous_tail = previous_chunk[-overlap:]
        max_check = min(len(previous_tail), len(current_chunk))

        for length in range(max_check, 0, -1):
            if current_chunk.startswith(previous_tail[-length:]):
                repeated_chars += length
                break

    return repeated_chars


def _ends_at_sentence_boundary(chunk: str) -> bool:
    """Return True when a chunk ends cleanly at common sentence punctuation."""
    return bool(re.search(r"[.!?。！？][\"')\]]?$", chunk.strip()))


def evaluate_chunking(text: str, chunk_size: int = 800, overlap: int = 100) -> ChunkingMetrics:
    """Evaluate one chunking setting using cheap, explainable metrics."""
    chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
    lengths = [len(chunk) for chunk in chunks]

    if not chunks:
        return ChunkingMetrics(
            chunk_size=chunk_size,
            overlap=overlap,
            chunk_count=0,
            average_chunk_length=0.0,
            max_chunk_length=0,
            size_utilization=0.0,
            repeated_character_ratio=0.0,
            sentence_boundary_ratio=0.0,
        )

    repeated_chars = _count_repeated_boundary_chars(chunks, overlap)
    total_chars = sum(lengths)
    sentence_boundary_count = sum(1 for chunk in chunks if _ends_at_sentence_boundary(chunk))

    return ChunkingMetrics(
        chunk_size=chunk_size,
        overlap=overlap,
        chunk_count=len(chunks),
        average_chunk_length=round(mean(lengths), 2),
        max_chunk_length=max(lengths),
        size_utilization=round(mean(length / chunk_size for length in lengths), 3),
        repeated_character_ratio=round(repeated_chars / total_chars, 3),
        sentence_boundary_ratio=round(sentence_boundary_count / len(chunks), 3),
    )


def compare_chunking_settings(
    text: str,
    settings: list[tuple[int, int]] | None = None,
) -> list[ChunkingMetrics]:
    """Compare several chunking settings on the same source text."""
    settings = settings or [(500, 50), (800, 100), (1200, 150)]
    return [evaluate_chunking(text, chunk_size=size, overlap=overlap) for size, overlap in settings]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a basic chunking evaluation on a text file.")
    parser.add_argument("input_file", type=Path, help="Plain-text filing content to evaluate.")
    parser.add_argument(
        "--settings",
        nargs="*",
        default=["500:50", "800:100", "1200:150"],
        help="Chunk settings in chunk_size:overlap format. Default: 500:50 800:100 1200:150",
    )
    args = parser.parse_args()

    text = args.input_file.read_text(encoding="utf-8")
    settings = []
    for raw_setting in args.settings:
        chunk_size, overlap = raw_setting.split(":", maxsplit=1)
        settings.append((int(chunk_size), int(overlap)))

    results = compare_chunking_settings(text, settings=settings)
    print(json.dumps([asdict(result) for result in results], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()