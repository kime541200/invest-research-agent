from __future__ import annotations

from invest_research_agent.research_models import OpportunityRoutingResult, ResearchAnswer


class OpportunityRouter:
    def route(self, answer: ResearchAnswer) -> OpportunityRoutingResult:
        text = " ".join(
            [
                answer.summary_answer,
                *[item.claim for item in answer.direct_mentions],
                *[item.claim for item in answer.inferred_points],
            ]
        ).casefold()

        warnings = [item.claim for item in answer.needs_validation]
        supporting_claims = [item.claim for item in answer.direct_mentions[:2]] or [item.claim for item in answer.inferred_points[:2]]

        if not answer.summary_answer and not answer.direct_mentions and not answer.inferred_points:
            return OpportunityRoutingResult(
                research_answer_path=answer.path,
                route="no_trade",
                rationale="缺少足夠的 answer-layer 訊號，尚無法形成可路由的投資機會。",
                supporting_claims=[],
                warnings=warnings,
            )

        if answer.needs_validation and not answer.direct_mentions and len(answer.inferred_points) <= 1:
            return OpportunityRoutingResult(
                research_answer_path=answer.path,
                route="macro_only",
                rationale="目前結論主要仍停留在待驗證或高不確定性狀態，先保留為研究追蹤。",
                supporting_claims=supporting_claims,
                warnings=warnings,
            )

        if any(keyword in text for keyword in ["odds", "probability", "election", "referendum", "approval", "rate cut", "cpi", "non-farm"]):
            return OpportunityRoutingResult(
                research_answer_path=answer.path,
                route="prediction_market",
                rationale="主要訊號可被事件化或條件化為明確 outcome，適合先進 prediction market 路線。",
                supporting_claims=supporting_claims,
                warnings=warnings,
            )

        if any(keyword in text for keyword in ["台灣", "台股", "taiwan", "twse", "台幣"]):
            return OpportunityRoutingResult(
                research_answer_path=answer.path,
                route="tw_equity",
                rationale="主要訊號與台灣政策、資產或本地市場主線有較強連結，適合先進台股 / 台灣資產路線。",
                supporting_claims=supporting_claims,
                warnings=warnings,
            )

        if any(keyword in text for keyword in ["nasdaq", "s&p", "etf", "equity", "stock", "earnings", "u.s.", "us "]):
            return OpportunityRoutingResult(
                research_answer_path=answer.path,
                route="us_equity",
                rationale="主要訊號可連到美股公司、ETF 或美股市場主線，適合先進美股路線。",
                supporting_claims=supporting_claims,
                warnings=warnings,
            )

        if answer.direct_mentions or answer.inferred_points:
            return OpportunityRoutingResult(
                research_answer_path=answer.path,
                route="macro_only",
                rationale="目前已有研究主線，但尚未清楚對應到可交易市場或標的，先保留為 macro / thematic tracking。",
                supporting_claims=supporting_claims,
                warnings=warnings,
            )

        return OpportunityRoutingResult(
            research_answer_path=answer.path,
            route="no_trade",
            rationale="目前內容不足以形成可執行投資機會。",
            supporting_claims=[],
            warnings=warnings,
        )
