from __future__ import annotations

from pathlib import Path

from info_collector.state_store import ResourceStateStore


def test_state_store_reads_optional_fields(tmp_path: Path) -> None:
    resource_file = tmp_path / "resources.yaml"
    resource_file.write_text(
        """
yt_channels:
  inside6202:
    url: https://www.youtube.com/@inside6202
    last_checked_video_title: old-title
    alias:
      - Inside
    tags:
      - 科技
      - AI
    always_watch: false
    description: 科技與商業趨勢
    topic_keywords:
      - 新創
      - SaaS
    priority: 3
    channel_id: UC123
""".strip()
        + "\n",
        encoding="utf-8",
    )

    store = ResourceStateStore(resource_file)
    channel = store.get_channel("inside6202")

    assert channel is not None
    assert channel.description == "科技與商業趨勢"
    assert channel.topic_keywords == ["新創", "SaaS"]
    assert channel.priority == 3
    assert channel.channel_id == "UC123"


def test_state_store_updates_last_checked_title(tmp_path: Path) -> None:
    resource_file = tmp_path / "resources.yaml"
    resource_file.write_text(
        """
yt_channels:
  Gooaye:
    url: https://www.youtube.com/@Gooaye
    last_checked_video_title: ""
    alias: []
    tags:
      - 投資
    always_watch: true
""".strip()
        + "\n",
        encoding="utf-8",
    )

    store = ResourceStateStore(resource_file)
    store.update_last_checked_title("Gooaye", "EP651")

    reloaded = ResourceStateStore(resource_file)
    channel = reloaded.get_channel("Gooaye")

    assert channel is not None
    assert channel.last_checked_video_title == "EP651"
