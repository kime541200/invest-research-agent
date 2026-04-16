from __future__ import annotations

from invest_research_agent.research_models import (
    OpportunityRoutingResult,
    PredictionMarketAnalysisResult,
    PredictionMarketCandidate,
    ResearchAnswer,
    ResearchAnswerPoint,
)


class PredictionMarketAnalyzer:
    def analyze(self, answer: ResearchAnswer, routing: OpportunityRoutingResult) -> PredictionMarketAnalysisResult:
        warnings = [*routing.warnings, *[item.claim for item in answer.needs_validation]]

        if routing.route != "prediction_market":
            return PredictionMarketAnalysisResult(
                research_answer_path=answer.path,
                route=routing.route,
                status="out_of_scope",
                summary="目前 research answer 未被路由到 prediction market lane。",
                warnings=warnings,
            )

        claim_sources = [
            *[("direct", item) for item in answer.direct_mentions],
            *[("inferred", item) for item in answer.inferred_points],
        ]
        seed_texts = [answer.summary_answer, *[item.claim for _, item in claim_sources]]
        seen: set[str] = set()
        candidates: list[PredictionMarketCandidate] = []
        direct_used = False

        for source_kind, item in claim_sources:
            candidate = self._candidate_from_point(item, routing, source_kind == "direct")
            if candidate is None:
                continue
            key = candidate.framing.casefold()
            if key in seen:
                continue
            seen.add(key)
            if source_kind == "direct":
                direct_used = True
            candidates.append(candidate)
            if len(candidates) >= 3:
                break

        if not candidates:
            for text in seed_texts:
                candidate = self._candidate_from_text(text, routing, source_claims=[])
                if candidate is None:
                    continue
                key = candidate.framing.casefold()
                if key in seen:
                    continue
                seen.add(key)
                candidates.append(candidate)
                if len(candidates) >= 3:
                    break

        if not candidates:
            return PredictionMarketAnalysisResult(
                research_answer_path=answer.path,
                route=routing.route,
                status="needs_review",
                summary="已路由到 prediction market，但目前無法穩定抽出可事件化的候選題目。",
                warnings=[*warnings, "缺少足夠明確的 event framing，需人工補充。"],
            )

        if not direct_used or answer.needs_validation:
            status = "needs_review"
            summary = "已產生 prediction market 候選題目，但仍建議人工確認 framing 與時間邊界。"
        else:
            status = "ready"
            summary = "已根據 research answer 產生可供 prediction market 研究的候選題目與搜尋 query。"

        return PredictionMarketAnalysisResult(
            research_answer_path=answer.path,
            route=routing.route,
            status=status,
            summary=summary,
            candidates=candidates,
            warnings=warnings,
        )

    def _candidate_from_point(
        self,
        point: ResearchAnswerPoint,
        routing: OpportunityRoutingResult,
        is_direct: bool,
    ) -> PredictionMarketCandidate | None:
        warnings: list[str] = []
        if not is_direct:
            warnings.append("這個 candidate 主要來自 inferred point，需人工確認事件邊界。")
        return self._candidate_from_text(
            point.claim,
            routing,
            source_claims=[point.claim],
            extra_warnings=warnings,
        )

    def _candidate_from_text(
        self,
        text: str,
        routing: OpportunityRoutingResult,
        *,
        source_claims: list[str],
        extra_warnings: list[str] | None = None,
    ) -> PredictionMarketCandidate | None:
        lowered = text.casefold()
        extra_warnings = extra_warnings or []

        if any(keyword in lowered for keyword in ["rate cut", "fomc", "fed", "升息", "降息"]):
            return PredictionMarketCandidate(
                framing="Will the next Fed decision be a rate cut?",
                search_queries=["next FOMC rate cut", "Fed cut next meeting", "rate cut probability", "Fed decision cut"],
                rationale=f"此候選題目來自可事件化的利率決策訊號；routing rationale: {routing.rationale}",
                source_claims=source_claims,
                warnings=[*extra_warnings, "若 answer 未提供會議時間，需人工確認 market resolution window。"],
            )

        if any(keyword in lowered for keyword in ["cpi", "inflation", "通膨"]):
            return PredictionMarketCandidate(
                framing="Will the next CPI print come in below consensus?",
                search_queries=["next CPI below consensus", "CPI inflation print", "next CPI forecast", "inflation surprise"],
                rationale=f"此候選題目來自可事件化的總經數據發布訊號；routing rationale: {routing.rationale}",
                source_claims=source_claims,
                warnings=[*extra_warnings, "需人工確認 consensus 基準與對應月份。"],
            )

        if any(keyword in lowered for keyword in ["non-farm", "payroll", "失業率", "employment", "jobs"]):
            return PredictionMarketCandidate(
                framing="Will the next U.S. jobs report beat expectations?",
                search_queries=["next non-farm payrolls", "jobs report beat expectations", "next payrolls surprise"],
                rationale=f"此候選題目來自可事件化的就業數據訊號；routing rationale: {routing.rationale}",
                source_claims=source_claims,
                warnings=[*extra_warnings, "需人工確認 market 使用的是 payrolls、失業率或其他就業指標。"],
            )

        if any(keyword in lowered for keyword in ["election", "選舉", "referendum", "投票"]):
            return PredictionMarketCandidate(
                framing="Will the referenced election outcome happen?",
                search_queries=["election winner market", "referendum outcome market", "election odds"],
                rationale=f"此候選題目來自明確可事件化的選舉 / 投票訊號；routing rationale: {routing.rationale}",
                source_claims=source_claims,
                warnings=[*extra_warnings, "需人工補上具體候選人、地區或投票名稱。"],
            )

        if any(keyword in lowered for keyword in ["approval", "approved", "核准", "通過"]):
            return PredictionMarketCandidate(
                framing="Will the referenced approval happen within the implied time window?",
                search_queries=["approval market", "regulatory approval odds", "approved this quarter"],
                rationale=f"此候選題目來自可事件化的 approval / regulatory signal；routing rationale: {routing.rationale}",
                source_claims=source_claims,
                warnings=[*extra_warnings, "需人工補上主管機關、標的與時間邊界。"],
            )

        if any(keyword in lowered for keyword in ["odds", "probability", "機率"]):
            return PredictionMarketCandidate(
                framing="Can this probability repricing be mapped to a binary market outcome?",
                search_queries=["probability repricing market", "odds shift market", "binary outcome market"],
                rationale=f"此候選題目來自機率變化訊號，但仍需人工確認對應事件；routing rationale: {routing.rationale}",
                source_claims=source_claims,
                warnings=[*extra_warnings, "目前只看到機率訊號，尚未自動抽出具體事件名稱。"],
            )

        return None


def render_prediction_market_analysis(result: PredictionMarketAnalysisResult) -> str:
    lines = [
        f"Route: {result.route}",
        f"Status: {result.status}",
        f"Summary: {result.summary}",
    ]
    if result.candidates:
        lines.append("Candidates:")
        for candidate in result.candidates:
            lines.append(f"- Framing: {candidate.framing}")
            lines.append(f"  Rationale: {candidate.rationale}")
            if candidate.source_claims:
                lines.append("  Source claims:")
                for claim in candidate.source_claims:
                    lines.append(f"    - {claim}")
            lines.append("  Search queries:")
            for query in candidate.search_queries:
                lines.append(f"    - {query}")
            if candidate.warnings:
                lines.append("  Warnings:")
                for warning in candidate.warnings:
                    lines.append(f"    - {warning}")
    if result.warnings:
        lines.append("Warnings:")
        for warning in result.warnings:
            lines.append(f"- {warning}")
    return "\n".join(lines)
