from __future__ import annotations

from pathlib import Path
import re

from invest_research_agent.research_models import ParsedNote

_NOTE_METADATA_PATTERN = re.compile(r"^- \*\*(.+?)：\*\* (.*)$")
_TOKEN_PATTERN = re.compile(r"[0-9A-Za-z][0-9A-Za-z.+_-]*|[\u4e00-\u9fff]{2,}")
_STOPWORDS = {
    "影片",
    "主題",
    "頻道",
    "來源",
    "日期",
    "字幕狀態",
    "字幕來源",
    "字幕語言",
    "待補",
    "這支影片",
    "本片",
}


def parse_markdown_note(path: Path | str) -> ParsedNote:
    note_path = Path(path)
    content = note_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    title = ""
    metadata: dict[str, str] = {}
    for line in lines:
        if line.startswith("# "):
            title = line[2:].strip()
            continue
        match = _NOTE_METADATA_PATTERN.match(line)
        if match:
            metadata[match.group(1).strip()] = match.group(2).strip()

    return ParsedNote(
        path=note_path,
        title=title,
        topic=metadata.get("主題", ""),
        channel=metadata.get("頻道", ""),
        source_url=metadata.get("來源", ""),
        content=content,
    )


def extract_note_keywords(note: ParsedNote, max_keywords: int = 5) -> list[str]:
    candidates = [note.title, note.topic, note.channel]
    joined = " ".join(value for value in candidates if value)
    seen: set[str] = set()
    keywords: list[str] = []

    for token in _TOKEN_PATTERN.findall(joined):
        normalized = token.strip()
        if not normalized or normalized in _STOPWORDS:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        keywords.append(normalized)
        if len(keywords) >= max_keywords:
            break
    return keywords
