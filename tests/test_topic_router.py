from __future__ import annotations

from invest_research_agent.models import ChannelConfig
from invest_research_agent.topic_router import TopicRouter


def test_topic_router_prefers_tag_and_keyword_matches() -> None:
    router = TopicRouter()
    channels = [
        ChannelConfig(
            name="inside6202",
            url="https://www.youtube.com/@inside6202",
            alias=["Inside", "Fox"],
            tags=["科技", "AI"],
            topic_keywords=["新創", "SaaS"],
            description="科技產業、AI 產品與商業模式",
            priority=1,
        ),
        ChannelConfig(
            name="Gooaye",
            url="https://www.youtube.com/@Gooaye",
            alias=["股癌"],
            tags=["投資", "理財"],
            description="股票與投資閒聊",
        ),
    ]

    routed = router.route("我想追蹤 AI 新創 與科技商業趨勢", channels, limit=2)

    assert routed[0].channel.name == "inside6202"
    assert "AI" in routed[0].matched_terms
    assert "新創" in routed[0].matched_terms


def test_topic_router_uses_priority_as_fallback() -> None:
    router = TopicRouter()
    channels = [
        ChannelConfig(name="low", url="https://example.com/low", priority=1),
        ChannelConfig(name="high", url="https://example.com/high", priority=5, watch_tier="core"),
    ]

    routed = router.route("完全無關的主題", channels, limit=2)

    assert routed[0].channel.name == "high"
    assert "priority" in routed[0].reason


def test_topic_router_excludes_paused_channels() -> None:
    router = TopicRouter()
    channels = [
        ChannelConfig(name="paused", url="https://example.com/paused", tags=["AI"], watch_tier="paused"),
        ChannelConfig(name="normal", url="https://example.com/normal", tags=["AI"], watch_tier="normal"),
    ]

    routed = router.route("AI", channels, limit=5)

    assert [item.channel.name for item in routed] == ["normal"]
