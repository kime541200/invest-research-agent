from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

from invest_research_agent.research_artifacts import ResearchArtifact
from invest_research_agent.research_models import ResearchAnswer, ResearchAnswerPoint


class ResearchAnswerStore:
    def build_path(self, *, artifact: ResearchArtifact, output_root: Path | str) -> Path:
        output_dir = Path(output_root) / artifact.path.parent.name
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir / artifact.path.name.replace(".research.json", ".answer.json")

    def write(self, answer: ResearchAnswer) -> Path:
        payload = asdict(answer)
        payload["path"] = str(answer.path)
        payload["research_artifact_path"] = str(answer.research_artifact_path)
        answer.path.parent.mkdir(parents=True, exist_ok=True)
        answer.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return answer.path

    def read(self, path: Path | str) -> ResearchAnswer:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return ResearchAnswer(
            path=Path(payload["path"]),
            question=payload.get("question", ""),
            research_artifact_path=Path(payload["research_artifact_path"]),
            title=payload.get("title", ""),
            channel=payload.get("channel", ""),
            topic=payload.get("topic", ""),
            summary_answer=payload.get("summary_answer", ""),
            direct_mentions=[ResearchAnswerPoint(**item) for item in payload.get("direct_mentions", [])],
            inferred_points=[ResearchAnswerPoint(**item) for item in payload.get("inferred_points", [])],
            needs_validation=[ResearchAnswerPoint(**item) for item in payload.get("needs_validation", [])],
            citations=payload.get("citations", []),
            notes=payload.get("notes", ""),
        )


class ResearchAnswerBuilder:
    def build_from_artifact(
        self,
        *,
        question: str,
        artifact: ResearchArtifact,
        output_path: Path | str,
    ) -> ResearchAnswer:
        direct_mentions = [
            ResearchAnswerPoint(claim=claim.text, evidence=list(claim.evidence_points))
            for claim in artifact.claims
        ]
        inferred_points = [
            ResearchAnswerPoint(
                claim=claim.text,
                reasoning="這個論點來自 research artifact 整理，仍需依具體問題判斷是否構成可執行結論。",
            )
            for claim in artifact.claims
            if claim.external_evidence
        ]
        needs_validation = [
            ResearchAnswerPoint(
                claim=claim.text,
                reason="仍缺少足夠外部驗證或更明確的投資映射。",
            )
            for claim in artifact.claims
            if claim.limitations or not claim.external_evidence
        ]
        summary_answer = "；".join(point.claim for point in direct_mentions[:3])
        citations = [f"{artifact.channel} / {artifact.title}"]
        return ResearchAnswer(
            path=Path(output_path),
            question=question,
            research_artifact_path=artifact.path,
            title=artifact.title,
            channel=artifact.channel,
            topic=artifact.topic,
            summary_answer=summary_answer,
            direct_mentions=direct_mentions,
            inferred_points=inferred_points,
            needs_validation=needs_validation,
            citations=citations,
        )


def render_research_answer(answer: ResearchAnswer) -> str:
    lines = [
        f"問題：{answer.question}",
        "",
        f"結論：{answer.summary_answer or '（無明確結論）'}",
    ]
    if answer.direct_mentions:
        lines.extend(["", "直接提到："])
        for item in answer.direct_mentions:
            lines.append(f"- {item.claim}")
            for evidence in item.evidence:
                lines.append(f"  - 依據：{evidence}")
    if answer.inferred_points:
        lines.extend(["", "推導："])
        for item in answer.inferred_points:
            lines.append(f"- {item.claim}")
            if item.reasoning:
                lines.append(f"  - 理由：{item.reasoning}")
    if answer.needs_validation:
        lines.extend(["", "待驗證："])
        for item in answer.needs_validation:
            lines.append(f"- {item.claim}")
            if item.reason:
                lines.append(f"  - 原因：{item.reason}")
    if answer.citations:
        lines.extend(["", "來源："])
        for citation in answer.citations:
            lines.append(f"- {citation}")
    if answer.notes:
        lines.extend(["", f"備註：{answer.notes}"])
    return "\n".join(lines)
