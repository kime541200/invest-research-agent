from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

import httpx

from invest_research_agent.research_models import ResearchEvidence


class ExternalResearchProvider(Protocol):
    def search(self, keywords: list[str], limit: int = 5) -> list[ResearchEvidence]:
        ...


@dataclass(frozen=True)
class _FeedEntry:
    title: str
    summary: str
    link: str
    published_at: str
    source: str


class RssResearchProvider:
    def __init__(self, feed_urls: list[str], timeout: float = 10.0) -> None:
        self.feed_urls = feed_urls
        self.timeout = timeout

    def search(self, keywords: list[str], limit: int = 5) -> list[ResearchEvidence]:
        cleaned_keywords = [keyword.strip() for keyword in keywords if keyword.strip()]
        if not cleaned_keywords:
            return []

        evidence: list[ResearchEvidence] = []
        for feed_url in self.feed_urls:
            for entry in _fetch_feed_entries(feed_url, timeout=self.timeout):
                score = _score_entry(entry, cleaned_keywords)
                if score <= 0:
                    continue
                evidence.append(
                    ResearchEvidence(
                        title=entry.title,
                        source=entry.source,
                        summary=entry.summary,
                        url=entry.link,
                        published_at=entry.published_at,
                        score=score,
                    )
                )

        evidence.sort(key=lambda item: (-item.score, item.source.casefold(), item.title.casefold()))
        deduped: list[ResearchEvidence] = []
        seen: set[tuple[str, str]] = set()
        for item in evidence:
            key = (item.url, item.title.casefold())
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
            if len(deduped) >= limit:
                break
        return deduped


def _fetch_feed_entries(feed_url: str, timeout: float) -> list[_FeedEntry]:
    response = httpx.get(feed_url, timeout=timeout)
    response.raise_for_status()

    root = ET.fromstring(response.text)
    entries: list[_FeedEntry] = []
    root_name = _get_local_name(root.tag)
    if root_name == "rss":
        channel = root.find("channel")
        source = _read_text(channel, "title") if channel is not None else ""
        for item in channel.findall("item") if channel is not None else []:
            entries.append(
                _FeedEntry(
                    title=_read_text(item, "title"),
                    summary=_read_text(item, "description"),
                    link=_read_text(item, "link"),
                    published_at=_read_text(item, "pubDate"),
                    source=source or _get_source_from_url(feed_url),
                )
            )
        return entries

    if root_name == "feed":
        source = _read_text(root, "title") or _get_source_from_url(feed_url)
        for entry in root.findall("{*}entry"):
            link = ""
            for link_node in entry.findall("{*}link"):
                href = link_node.attrib.get("href", "").strip()
                if href:
                    link = href
                    break
            entries.append(
                _FeedEntry(
                    title=_read_text(entry, "title"),
                    summary=_read_text(entry, "summary") or _read_text(entry, "content"),
                    link=link,
                    published_at=_read_text(entry, "published") or _read_text(entry, "updated"),
                    source=source,
                )
            )
        return entries

    return entries


def _read_text(node: ET.Element | None, child_name: str) -> str:
    if node is None:
        return ""
    child = node.find(child_name)
    if child is None:
        child = node.find(f"{{*}}{child_name}")
    if child is None or child.text is None:
        return ""
    return child.text.strip()


def _get_local_name(tag: str) -> str:
    return tag.rsplit("}", maxsplit=1)[-1]


def _score_entry(entry: _FeedEntry, keywords: list[str]) -> float:
    haystack = f"{entry.title}\n{entry.summary}".casefold()
    score = 0.0
    for keyword in keywords:
        normalized = keyword.casefold()
        if normalized in haystack:
            score += 2.0 if normalized in entry.title.casefold() else 1.0
    return score


def _get_source_from_url(feed_url: str) -> str:
    hostname = urlparse(feed_url).hostname or ""
    return hostname.removeprefix("www.")
