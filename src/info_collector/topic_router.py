from __future__ import annotations

import re
from collections.abc import Iterable

from info_collector.models import ChannelConfig, RoutedChannel


class TopicRouter:
    def route(
        self,
        topic: str,
        channels: Iterable[ChannelConfig],
        limit: int | None = None,
    ) -> list[RoutedChannel]:
        topic_text = topic.strip()
        if not topic_text:
            return []

        topic_tokens = set(_tokenize(topic_text))
        routed: list[RoutedChannel] = []

        for channel in channels:
            score, matched_terms, reason = self._score_channel(channel, topic_text, topic_tokens)
            if score <= 0:
                continue
            routed.append(
                RoutedChannel(
                    channel=channel,
                    score=score,
                    matched_terms=matched_terms,
                    reason=reason,
                )
            )

        routed.sort(
            key=lambda item: (
                -item.score,
                not item.channel.always_watch,
                item.channel.name.lower(),
            )
        )

        if routed:
            return routed[:limit] if limit is not None else routed

        fallback = [
            RoutedChannel(
                channel=channel,
                score=float(max(channel.priority, 0)),
                matched_terms=[],
                reason="找不到明確標籤命中，改用 priority 與 always_watch 做保守排序。",
            )
            for channel in channels
        ]
        fallback.sort(
            key=lambda item: (
                not item.channel.always_watch,
                -item.channel.priority,
                item.channel.name.lower(),
            )
        )
        return fallback[:limit] if limit is not None else fallback

    def _score_channel(
        self,
        channel: ChannelConfig,
        topic_text: str,
        topic_tokens: set[str],
    ) -> tuple[float, list[str], str]:
        score = float(max(channel.priority, 0))
        matched_terms: list[str] = []
        reasons: list[str] = []
        topic_lower = topic_text.casefold()

        if channel.priority > 0:
            reasons.append(f"priority 加權: {channel.priority}")

        name_candidates = [channel.name, *channel.alias]
        matched_names = [item for item in name_candidates if item and item.casefold() in topic_lower]
        if matched_names:
            score += 6.0 + (len(matched_names) - 1)
            matched_terms.extend(matched_names)
            reasons.append(f"別名/頻道命中: {', '.join(matched_names)}")

        matched_tags = [tag for tag in channel.tags if tag.casefold() in topic_lower or tag.casefold() in topic_tokens]
        if matched_tags:
            score += len(matched_tags) * 4.0
            matched_terms.extend(matched_tags)
            reasons.append(f"標籤命中: {', '.join(matched_tags)}")

        matched_keywords = [
            keyword
            for keyword in channel.topic_keywords
            if keyword.casefold() in topic_lower or keyword.casefold() in topic_tokens
        ]
        if matched_keywords:
            score += len(matched_keywords) * 3.0
            matched_terms.extend(matched_keywords)
            reasons.append(f"關鍵詞命中: {', '.join(matched_keywords)}")

        description_tokens = set(_tokenize(channel.description))
        description_hits = sorted(topic_tokens.intersection(description_tokens))
        if description_hits:
            score += min(len(description_hits), 3) * 1.5
            matched_terms.extend(description_hits)
            reasons.append(f"描述補強: {', '.join(description_hits[:3])}")

        if score > 0 and channel.always_watch:
            score += 0.5
            reasons.append("always_watch 加權")

        deduped_terms = _dedupe_preserving_order(matched_terms)
        reason = "；".join(reasons) if reasons else "由 priority 提供基礎排序。"
        return score, deduped_terms, reason


def _tokenize(text: str) -> list[str]:
    return [token.casefold() for token in re.findall(r"[0-9A-Za-z_]+|[\u4e00-\u9fff]+", text)]


def _dedupe_preserving_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        key = item.casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped
