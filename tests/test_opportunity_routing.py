from __future__ import annotations

from pathlib import Path

from invest_research_agent.opportunity_routing import OpportunityRouter
from invest_research_agent.research_models import ResearchAnswer, ResearchAnswerPoint


def _answer(*, summary: str = "", direct: list[ResearchAnswerPoint] | None = None, inferred: list[ResearchAnswerPoint] | None = None, validation: list[ResearchAnswerPoint] | None = None) -> ResearchAnswer:
    return ResearchAnswer(
        path=Path("/tmp/sample.answer.json"),
        question="測試問題",
        research_artifact_path=Path("/tmp/sample.research.json"),
        title="sample",
        channel="sample-channel",
        topic="sample-topic",
        summary_answer=summary,
        direct_mentions=direct or [],
        inferred_points=inferred or [],
        needs_validation=validation or [],
    )


def test_router_routes_prediction_market() -> None:
    result = OpportunityRouter().route(
        _answer(summary="The main signal is a rate cut probability repricing.")
    )
    assert result.route == "prediction_market"


def test_router_routes_tw_equity() -> None:
    result = OpportunityRouter().route(
        _answer(summary="台灣政策變化可能影響台股與台幣相關資產。")
    )
    assert result.route == "tw_equity"


def test_router_routes_us_equity() -> None:
    result = OpportunityRouter().route(
        _answer(summary="This theme should be tracked through U.S. equity and ETF exposure.")
    )
    assert result.route == "us_equity"


def test_router_routes_macro_only_when_signals_exist_without_asset_lane() -> None:
    result = OpportunityRouter().route(
        _answer(
            summary="這是一條值得追蹤的產業主線。",
            inferred=[ResearchAnswerPoint(claim="基礎設施 adoption 持續上升。", reasoning="來自研究推導")],
        )
    )
    assert result.route == "macro_only"


def test_router_routes_no_trade_when_answer_lacks_signal() -> None:
    result = OpportunityRouter().route(_answer())
    assert result.route == "no_trade"


def test_router_downgrades_when_validation_dominates() -> None:
    result = OpportunityRouter().route(
        _answer(
            validation=[ResearchAnswerPoint(claim="尚待驗證的政策訊號", reason="資料不足")],
            inferred=[ResearchAnswerPoint(claim="可能存在機會", reasoning="但不夠穩")],
        )
    )
    assert result.route == "macro_only"
    assert result.warnings == ["尚待驗證的政策訊號"]
