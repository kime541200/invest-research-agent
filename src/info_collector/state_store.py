from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from info_collector.models import ChannelConfig, ChannelState, WatchTier

WATCH_TIER_ORDER: dict[str, int] = {
    "core": 0,
    "normal": 1,
    "optional": 2,
    "paused": 3,
}


class ResourceStateStore:
    def __init__(self, resource_path: Path | str) -> None:
        self.resource_path = Path(resource_path)

    def get_channels(self) -> list[ChannelConfig]:
        data = self._load_raw()
        channels = data.get("yt_channels", {})
        channel_state = data.get("channel_state", {})
        return [
            self._to_channel_config(name, info, channel_state.get(name, {}))
            for name, info in channels.items()
        ]

    def get_channel(self, channel_name: str) -> ChannelConfig | None:
        data = self._load_raw()
        info = data.get("yt_channels", {}).get(channel_name)
        if info is None:
            return None
        state = data.get("channel_state", {}).get(channel_name, {})
        return self._to_channel_config(channel_name, info, state)

    def get_all_tags(self) -> list[str]:
        tags: set[str] = set()
        for channel in self.get_channels():
            tags.update(channel.tags)
        return sorted(tags)

    def get_channels_by_tags(self, tags: list[str], include_paused: bool = False) -> dict[str, list[ChannelConfig]]:
        target_tags = {tag.strip() for tag in tags if tag.strip()}
        grouped: dict[str, list[ChannelConfig]] = {tier: [] for tier in WATCH_TIER_ORDER}

        for channel in self.get_channels():
            if channel.watch_tier == "paused" and not include_paused:
                continue
            if target_tags.intersection(channel.tags):
                grouped.setdefault(channel.watch_tier, []).append(channel)

        for tier_channels in grouped.values():
            tier_channels.sort(key=lambda channel: (-channel.priority, channel.name.lower()))
        return {tier: channels for tier, channels in grouped.items() if channels}

    def update_last_checked_title(self, channel_name: str, title: str) -> None:
        data = self._load_raw()
        channels = data.setdefault("yt_channels", {})
        if channel_name not in channels:
            raise KeyError(f"找不到頻道: {channel_name}")
        channel_state = data.setdefault("channel_state", {})
        state = channel_state.setdefault(channel_name, {})
        state["last_checked_video_title"] = title
        self._write_raw(data)

    def update_channel_id(self, channel_name: str, channel_id: str) -> None:
        data = self._load_raw()
        channels = data.setdefault("yt_channels", {})
        if channel_name not in channels:
            raise KeyError(f"找不到頻道: {channel_name}")
        channel_state = data.setdefault("channel_state", {})
        state = channel_state.setdefault(channel_name, {})
        state["channel_id"] = channel_id
        self._write_raw(data)

    def _load_raw(self) -> dict[str, Any]:
        if not self.resource_path.exists():
            raise FileNotFoundError(f"找不到檔案: {self.resource_path}")

        with self.resource_path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}

        if not isinstance(data, dict):
            raise ValueError("resources.yaml 必須是物件結構")

        return data

    def _write_raw(self, data: dict[str, Any]) -> None:
        with self.resource_path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(data, handle, allow_unicode=True, sort_keys=False)

    def _to_channel_config(self, name: str, info: dict[str, Any], state: dict[str, Any]) -> ChannelConfig:
        channel_state = self._to_channel_state(info, state)
        return ChannelConfig(
            name=name,
            url=str(info.get("url", "")),
            alias=[str(item) for item in info.get("alias", [])],
            tags=[str(item) for item in info.get("tags", [])],
            watch_tier=_normalize_watch_tier(info),
            description=str(info.get("description", "")),
            topic_keywords=[str(item) for item in info.get("topic_keywords", [])],
            priority=int(info.get("priority", 0) or 0),
            last_checked_video_title=channel_state.last_checked_video_title,
            channel_id=channel_state.channel_id,
        )

    def _to_channel_state(self, info: dict[str, Any], state: dict[str, Any]) -> ChannelState:
        state_info = state if isinstance(state, dict) else {}
        return ChannelState(
            last_checked_video_title=str(
                state_info.get("last_checked_video_title", info.get("last_checked_video_title", ""))
            ),
            channel_id=_normalize_optional_str(state_info.get("channel_id", info.get("channel_id"))),
        )


def _normalize_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_watch_tier(info: dict[str, Any]) -> WatchTier:
    raw_watch_tier = str(info.get("watch_tier", "")).strip().casefold()
    if raw_watch_tier in WATCH_TIER_ORDER:
        return raw_watch_tier  # type: ignore[return-value]

    if "always_watch" in info:
        return "core" if bool(info.get("always_watch", False)) else "normal"

    return "normal"
