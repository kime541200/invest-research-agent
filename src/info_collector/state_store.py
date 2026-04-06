from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from info_collector.models import ChannelConfig


class ResourceStateStore:
    def __init__(self, resource_path: Path | str) -> None:
        self.resource_path = Path(resource_path)

    def get_channels(self) -> list[ChannelConfig]:
        data = self._load_raw()
        channels = data.get("yt_channels", {})
        return [self._to_channel_config(name, info) for name, info in channels.items()]

    def get_channel(self, channel_name: str) -> ChannelConfig | None:
        data = self._load_raw()
        info = data.get("yt_channels", {}).get(channel_name)
        if info is None:
            return None
        return self._to_channel_config(channel_name, info)

    def get_all_tags(self) -> list[str]:
        tags: set[str] = set()
        for channel in self.get_channels():
            tags.update(channel.tags)
        return sorted(tags)

    def get_channels_by_tags(self, tags: list[str]) -> tuple[list[ChannelConfig], list[ChannelConfig]]:
        target_tags = {tag.strip() for tag in tags if tag.strip()}
        always_watch: list[ChannelConfig] = []
        optional_watch: list[ChannelConfig] = []

        for channel in self.get_channels():
            if target_tags.intersection(channel.tags):
                if channel.always_watch:
                    always_watch.append(channel)
                else:
                    optional_watch.append(channel)

        return always_watch, optional_watch

    def update_last_checked_title(self, channel_name: str, title: str) -> None:
        data = self._load_raw()
        channels = data.setdefault("yt_channels", {})
        if channel_name not in channels:
            raise KeyError(f"找不到頻道: {channel_name}")
        channels[channel_name]["last_checked_video_title"] = title
        self._write_raw(data)

    def update_channel_id(self, channel_name: str, channel_id: str) -> None:
        data = self._load_raw()
        channels = data.setdefault("yt_channels", {})
        if channel_name not in channels:
            raise KeyError(f"找不到頻道: {channel_name}")
        channels[channel_name]["channel_id"] = channel_id
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

    def _to_channel_config(self, name: str, info: dict[str, Any]) -> ChannelConfig:
        return ChannelConfig(
            name=name,
            url=str(info.get("url", "")),
            last_checked_video_title=str(info.get("last_checked_video_title", "")),
            alias=[str(item) for item in info.get("alias", [])],
            tags=[str(item) for item in info.get("tags", [])],
            always_watch=bool(info.get("always_watch", False)),
            description=str(info.get("description", "")),
            topic_keywords=[str(item) for item in info.get("topic_keywords", [])],
            priority=int(info.get("priority", 0) or 0),
            channel_id=str(info["channel_id"]) if info.get("channel_id") else None,
        )
