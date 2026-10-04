"""Chunk a KNOWLEDGE.md into one chunk per H3 subsection.

Expects the template produced by the `contexta-init` skill: a single H1
("# KNOWLEDGE: <service>"), one or more H2 sections, each with H3
subsections. Body of each H3 is treated as the chunk text.

Chunks are skipped when the body is empty, a `_TBD_` placeholder, or a
single `N/A — ...` line — no signal to embed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Chunk:
    section: str
    subsection: str
    text: str


@dataclass
class ParsedKnowledge:
    service_name: str | None
    chunks: list[Chunk]
    skipped: int


_H1 = re.compile(r"^# KNOWLEDGE:\s*(.+?)\s*$", re.MULTILINE)
_PLACEHOLDER_RE = re.compile(r"^(?:_TBD_|_WIP_|N/A\b.*)$", re.IGNORECASE)


def _strip_comments_and_blanks(text: str) -> str:
    # Drop HTML comment blocks and surrounding whitespace.
    without_comments = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    return without_comments.strip()


def _is_placeholder(body: str) -> bool:
    stripped = _strip_comments_and_blanks(body)
    if not stripped:
        return True
    # Treat as placeholder if the only non-empty line is _TBD_ or "N/A …".
    lines = [ln.strip() for ln in stripped.splitlines() if ln.strip()]
    return len(lines) == 1 and bool(_PLACEHOLDER_RE.match(lines[0]))


def parse(markdown: str) -> ParsedKnowledge:
    # Service name from H1.
    service_name: str | None = None
    m = _H1.search(markdown)
    if m:
        candidate = m.group(1).strip()
        if candidate and not candidate.startswith("<"):  # ignore <SERVICE_NAME> stub
            service_name = candidate

    # Walk lines, tracking current H2 (section) and H3 (subsection).
    chunks: list[Chunk] = []
    skipped = 0
    current_section: str | None = None
    current_subsection: str | None = None
    body_buf: list[str] = []
    in_fence = False
    fence_marker: str | None = None

    def flush() -> None:
        nonlocal skipped
        if current_section is None or current_subsection is None:
            return
        body = "\n".join(body_buf).strip()
        if _is_placeholder(body):
            skipped += 1
            return
        chunks.append(
            Chunk(
                section=current_section,
                subsection=current_subsection,
                text=body,
            )
        )

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()

        # Track fenced code blocks so ## inside a code block isn't a heading.
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            marker = stripped[:3]
            if not in_fence:
                in_fence = True
                fence_marker = marker
            elif marker == fence_marker:
                in_fence = False
                fence_marker = None
            body_buf.append(raw_line)
            continue

        if not in_fence and line.startswith("## ") and not line.startswith("### "):
            flush()
            current_section = line[3:].strip()
            current_subsection = None
            body_buf = []
            continue

        if not in_fence and line.startswith("### "):
            flush()
            current_subsection = line[4:].strip()
            body_buf = []
            continue

        body_buf.append(raw_line)

    flush()
    return ParsedKnowledge(
        service_name=service_name, chunks=chunks, skipped=skipped
    )