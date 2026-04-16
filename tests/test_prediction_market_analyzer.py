from __future__ import annotations

from pathlib import Path

from invest_research_agent.opportunity_routing import OpportunityRouter
from invest_research_agent.prediction_market_analyzer import PredictionMarketAnalyzer
from invest_research_agent.research_models import OpportunityRoutingResult, ResearchAnswer, ResearchAnswerPoint


def _answer(
    *,
    summary: str = "",
    direct: list[ResearchAnswerPoint] | None = None,
    inferred: list[ResearchAnswerPoint] | None = None,
    validation: list[ResearchAnswerPoint] | None = None,
) -> ResearchAnswer:
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


def test_prediction_market_analyzer_generates_candidate_for_rate_cut() -> None:
    answer = _answer(
        summary="The main signal is a rate cut probability repricing.",
        direct=[ResearchAnswerPoint(claim="Fed rate cut odds are being repriced.")],
    )

    result = PredictionMarketAnalyzer().analyze(answer, OpportunityRouter().route(answer))

    assert result.route == "prediction_market"
    assert result.status == "ready"
    assert result.candidates
    assert result.candidates[0].framing == "Will the next Fed decision be a rate cut?"
    assert "next FOMC rate cut" in result.candidates[0].search_queries


def test_prediction_market_analyzer_returns_out_of_scope_for_non_prediction_route() -> None:
    answer = _answer(summary="This theme should be tracked through U.S. equity and ETF exposure.")

    result = PredictionMarketAnalyzer().analyze(answer, OpportunityRouter().route(answer))

    assert result.status == "out_of_scope"
    assert result.candidates == []


def test_prediction_market_analyzer_marks_needs_review_for_inferred_only_signal() -> None:
    answer = _answer(
        summary="The market may be repricing the next CPI event.",
        inferred=[ResearchAnswerPoint(claim="CPI could come in softer than expected.", reasoning="由研究推導")],
    )
    routing = OpportunityRoutingResult(
        research_answer_path=answer.path,
        route="prediction_market",
        rationale="這是一個可事件化的總經數據訊號。",
        warnings=[],
    )

    result = PredictionMarketAnalyzer().analyze(answer, routing)

    assert result.status == "needs_review"
    assert result.candidates
    assert "需人工確認事件邊界" in " ".join(result.candidates[0].warnings)


def test_prediction_market_analyzer_propagates_validation_warnings() -> None:
    answer = _answer(
        summary="The main signal is a rate cut probability repricing.",
        direct=[ResearchAnswerPoint(claim="Fed rate cut odds are being repriced.")],
        validation=[ResearchAnswerPoint(claim="會議時間仍待確認", reason="時間窗口不明")],
    )

    result = PredictionMarketAnalyzer().analyze(answer, OpportunityRouter().route(answer))

    assert "會議時間仍待確認" in result.warnings
    assert result.status == "needs_review"
