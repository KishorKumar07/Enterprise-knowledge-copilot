"""Structure-aware chunking.

Splits on natural document boundaries (markdown headings, then paragraphs)
before falling back to a fixed-size sliding window, so chunks stay aligned
with the document's actual structure instead of cutting mid-sentence.
"""

import re
from dataclasses import dataclass, field

TARGET_CHUNK_CHARS = 1000
OVERLAP_CHARS = 150
MIN_CHUNK_CHARS = 80

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)


@dataclass
class Chunk:
    content: str
    index: int
    metadata: dict = field(default_factory=dict)


def _split_into_sections(text: str) -> list[tuple[str | None, str]]:
    """Split on markdown headings; returns (heading_or_none, section_text) pairs."""
    matches = list(HEADING_RE.finditer(text))
    if not matches:
        return [(None, text)]

    sections: list[tuple[str | None, str]] = []
    if matches[0].start() > 0:
        sections.append((None, text[: matches[0].start()]))

    for i, match in enumerate(matches):
        heading = match.group(2).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections.append((heading, text[start:end]))

    return sections


def _split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def _pack_paragraphs(paragraphs: list[str]) -> list[str]:
    """Greedily pack paragraphs into ~TARGET_CHUNK_CHARS windows with overlap."""
    packed: list[str] = []
    current = ""

    for paragraph in paragraphs:
        if len(paragraph) > TARGET_CHUNK_CHARS:
            if current:
                packed.append(current)
                current = ""
            # Hard-wrap an oversized paragraph with a sliding window.
            start = 0
            while start < len(paragraph):
                end = start + TARGET_CHUNK_CHARS
                packed.append(paragraph[start:end])
                start = end - OVERLAP_CHARS
            continue

        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) <= TARGET_CHUNK_CHARS:
            current = candidate
        else:
            if current:
                packed.append(current)
            current = paragraph

    if current:
        packed.append(current)

    return packed


def chunk_text(text: str, base_metadata: dict | None = None) -> list[Chunk]:
    text = text.strip()
    if not text:
        return []

    base_metadata = base_metadata or {}
    chunks: list[Chunk] = []
    index = 0

    for heading, section_text in _split_into_sections(text):
        paragraphs = _split_paragraphs(section_text)
        if not paragraphs:
            continue

        for packed in _pack_paragraphs(paragraphs):
            content = packed.strip()
            if len(content) < MIN_CHUNK_CHARS and chunks:
                # Too small to stand alone — merge into the previous chunk.
                chunks[-1].content = f"{chunks[-1].content}\n\n{content}"
                continue

            metadata = {**base_metadata}
            if heading:
                metadata["section"] = heading

            chunks.append(Chunk(content=content, index=index, metadata=metadata))
            index += 1

    return chunks
