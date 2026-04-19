from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path

from invest_research_agent.analysis_artifacts import AnalysisArtifactStore
from invest_research_agent.audio_downloader import AudioDownloader, load_audio_cache_settings
from invest_research_agent.external_research import RssResearchProvider
from invest_research_agent.mcp_client import McpHttpClient
from invest_research_agent.note_generator import MarkdownNoteGenerator, NoteContext
from invest_research_agent.orchestrator import CollectorOrchestrator
from invest_research_agent.prediction_market_analyzer import PredictionMarketAnalyzer, render_prediction_market_analysis
from invest_research_agent.research_answers import ResearchAnswerBuilder, ResearchAnswerStore, render_research_answer
from invest_research_agent.research_artifacts import ResearchArtifactStore
from invest_research_agent.opportunity_routing import OpportunityRouter
from invest_research_agent.research_pipeline import ResearchNoteEnricher, write_enrichment_result
from invest_research_agent.state_store import ResourceStateStore
from invest_research_agent.stt import SttClient, check_stt_provider, load_stt_settings
from invest_research_agent.transcript_artifacts import artifact_to_note_context_data, read_transcript_artifact
from invest_research_agent.topic_router import TopicRouter
from invest_research_agent.video_fetcher import YouTubeMcpGateway


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    if not hasattr(args, "handler"):
        parser.print_help()
        return

    requires_orchestrator = getattr(args, "requires_orchestrator", True)
    orchestrator = _build_orchestrator(args) if requires_orchestrator else None
    args.handler(args, orchestrator)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Topic-driven investment research agent")
    parser.add_argument(
        "--resources-file",
        default="resources.yaml",
        help="resources.yaml 路徑",
    )
    parser.add_argument(
        "--notes-dir",
        default="notes",
        help="筆記輸出目錄",
    )
    parser.add_argument(
        "--transcripts-dir",
        default="transcripts",
        help="逐字稿 artifact 輸出目錄",
    )
    parser.add_argument(
        "--analysis-dir",
        default="analysis",
        help="analysis artifact 輸出目錄",
    )
    parser.add_argument(
        "--mcp-url",
        default="http://localhost:8088/mcp",
        help="yt-mcp-server HTTP endpoint",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="MCP 連線 timeout 秒數",
    )
    parser.add_argument(
        "--cache-dir",
        default=".cache/invest-research-agent",
        help="快取輸出目錄（音訊下載等）",
    )

    subparsers = parser.add_subparsers(dest="command")

    route_topic = subparsers.add_parser("route-topic", help="根據主題推薦頻道")
    route_topic.add_argument("--topic", required=True, help="使用者主題描述")
    route_topic.add_argument("--limit", type=int, default=5, help="回傳頻道數量")
    route_topic.add_argument("--json", action="store_true", help="輸出 JSON")
    route_topic.set_defaults(handler=_handle_route_topic)

    collect_topic = subparsers.add_parser("collect-from-topic", help="從主題收集影片並產出筆記")
    collect_topic.add_argument("--topic", required=True, help="使用者主題描述")
    collect_topic.add_argument("--max-channels", type=int, default=3, help="最多處理幾個頻道")
    collect_topic.add_argument("--max-videos-per-channel", type=int, default=5, help="每個頻道抓幾支最新影片")
    collect_topic.add_argument("--initial-video-limit", type=int, default=1, help="第一次處理頻道時最多抓幾支")
    collect_topic.add_argument("--transcript-language", default=None, help="字幕語言，例如 zh-TW")
    collect_topic.add_argument("--dry-run", action="store_true", help="只模擬流程，不寫 notes 也不更新狀態")
    collect_topic.add_argument("--json", action="store_true", help="輸出 JSON")
    collect_topic.set_defaults(handler=_handle_collect_topic)

    export_topic = subparsers.add_parser("export-transcripts-from-topic", help="從主題收集影片並輸出 transcript artifacts")
    export_topic.add_argument("--topic", required=True, help="使用者主題描述")
    export_topic.add_argument("--max-channels", type=int, default=3, help="最多處理幾個頻道")
    export_topic.add_argument("--max-videos-per-channel", type=int, default=5, help="每個頻道抓幾支最新影片")
    export_topic.add_argument("--initial-video-limit", type=int, default=1, help="第一次處理頻道時最多抓幾支")
    export_topic.add_argument("--transcript-language", default=None, help="字幕語言，例如 zh-TW")
    export_topic.add_argument("--dry-run", action="store_true", help="只模擬流程，不更新狀態")
    export_topic.add_argument("--json", action="store_true", help="輸出 JSON")
    export_topic.set_defaults(handler=_handle_export_transcripts)

    list_tags = subparsers.add_parser("list-tags", help="列出所有 tags")
    list_tags.add_argument("--json", action="store_true", help="輸出 JSON")
    list_tags.set_defaults(handler=_handle_list_tags)

    list_channels = subparsers.add_parser("list-channels", help="列出所有頻道")
    list_channels.add_argument(
        "--watch-tier",
        choices=["core", "normal", "optional", "paused"],
        default=None,
        help="只列出指定 watch_tier 的頻道",
    )
    list_channels.add_argument("--include-paused", action="store_true", help="包含 paused 頻道")
    list_channels.add_argument("--json", action="store_true", help="輸出 JSON")
    list_channels.set_defaults(handler=_handle_list_channels)

    get_channel_tags = subparsers.add_parser("get-channel-tags", help="取得指定頻道的 tags")
    get_channel_tags.add_argument("--channel", required=True, help="頻道名稱")
    get_channel_tags.add_argument("--json", action="store_true", help="輸出 JSON")
    get_channel_tags.set_defaults(handler=_handle_get_channel_tags)

    channels_by_tags = subparsers.add_parser("get-channels-by-tags", help="依 tags 列出頻道")
    channels_by_tags.add_argument("--tags", nargs="+", required=True, help="一個或多個 tags")
    channels_by_tags.add_argument("--include-paused", action="store_true", help="包含 paused 頻道")
    channels_by_tags.add_argument("--json", action="store_true", help="輸出 JSON")
    channels_by_tags.set_defaults(handler=_handle_get_channels_by_tags)

    get_last_checked = subparsers.add_parser("get-last-checked", help="查詢頻道最後確認的影片標題")
    get_last_checked.add_argument("--channel", required=True, help="頻道名稱")
    get_last_checked.add_argument("--json", action="store_true", help="輸出 JSON")
    get_last_checked.set_defaults(handler=_handle_get_last_checked)

    update_last_checked = subparsers.add_parser("update-last-checked", help="更新頻道最後確認的影片標題")
    update_last_checked.add_argument("--channel", required=True, help="頻道名稱")
    update_last_checked.add_argument("--title", required=True, help="新的影片標題")
    update_last_checked.set_defaults(handler=_handle_update_last_checked)

    check_stt = subparsers.add_parser("check-stt", help="檢查 STT provider 設定與健康狀態")
    check_stt.add_argument("--json", action="store_true", help="輸出 JSON")
    check_stt.set_defaults(handler=_handle_check_stt, requires_orchestrator=False)

    enrich_notes = subparsers.add_parser("enrich-notes", help="為既有筆記補充外部研究證據")
    enrich_notes.add_argument("--note-paths", nargs="*", default=None, help="指定一個或多個 note 路徑")
    enrich_notes.add_argument("--date", default=None, help="只處理 notes/YYYY-MM-DD 內的筆記")
    enrich_notes.add_argument("--rss-feed", nargs="+", required=True, help="一個或多個 RSS / Atom feed URL")
    enrich_notes.add_argument("--keywords", nargs="*", default=None, help="覆蓋自動抽出的關鍵字")
    enrich_notes.add_argument("--limit", type=int, default=5, help="每篇筆記最多保留幾筆外部證據")
    enrich_notes.add_argument("--json", action="store_true", help="輸出 JSON，不寫 sidecar 檔")
    enrich_notes.set_defaults(handler=_handle_enrich_notes, requires_orchestrator=False)

    prepare_analysis = subparsers.add_parser("prepare-analysis", help="為 transcript artifact 初始化 analysis artifact")
    prepare_analysis.add_argument("--transcript-path", required=True, help="transcript artifact 路徑")
    prepare_analysis.add_argument("--output-path", default=None, help="analysis artifact 輸出路徑")
    prepare_analysis.add_argument("--json", action="store_true", help="輸出 JSON")
    prepare_analysis.set_defaults(handler=_handle_prepare_analysis, requires_orchestrator=False)

    render_note = subparsers.add_parser("render-note", help="從 transcript artifact 與 analysis artifact 組裝最終筆記")
    render_note.add_argument("--transcript-path", required=True, help="transcript artifact 路徑")
    render_note.add_argument("--analysis-path", default=None, help="analysis artifact 路徑")
    render_note.add_argument("--json", action="store_true", help="輸出 JSON")
    render_note.set_defaults(handler=_handle_render_note, requires_orchestrator=False)

    synthesize_answer = subparsers.add_parser("synthesize-answer", help="為 agent-first answer synthesis 準備 research answer workflow")
    synthesize_answer.add_argument("--research-artifact-path", required=True, help="research artifact 路徑")
    synthesize_answer.add_argument("--question", required=True, help="使用者研究問題")
    synthesize_answer.add_argument("--output-path", default=None, help="research answer 輸出路徑")
    synthesize_answer.add_argument("--json", action="store_true", help="輸出 JSON")
    synthesize_answer.set_defaults(handler=_handle_synthesize_answer, requires_orchestrator=False)

    analyze_prediction_market = subparsers.add_parser("analyze-prediction-market", help="從 research answer 產生 prediction market 候選題目")
    analyze_prediction_market.add_argument("--research-answer-path", required=True, help="research answer 路徑")
    analyze_prediction_market.add_argument("--output-path", default=None, help="prediction market analysis 輸出路徑")
    analyze_prediction_market.add_argument("--json", action="store_true", help="輸出 JSON")
    analyze_prediction_market.set_defaults(handler=_handle_analyze_prediction_market, requires_orchestrator=False)

    return parser


def _build_orchestrator(args: argparse.Namespace) -> CollectorOrchestrator:
    project_root = Path.cwd()
    resources_file = _resolve_project_path(project_root, args.resources_file)
    notes_dir = _resolve_project_path(project_root, args.notes_dir)
    transcripts_dir = _resolve_project_path(project_root, args.transcripts_dir)
    analysis_dir = _resolve_project_path(project_root, args.analysis_dir)
    cache_dir = _resolve_project_path(project_root, args.cache_dir)

    state_store = ResourceStateStore(resources_file)
    topic_router = TopicRouter()
    client = McpHttpClient(endpoint=args.mcp_url, timeout=args.timeout)
    gateway = YouTubeMcpGateway(client)
    note_generator = MarkdownNoteGenerator()
    stt_settings = load_stt_settings(project_root)
    stt_client = SttClient(stt_settings) if stt_settings is not None else None
    audio_cache_settings = load_audio_cache_settings(project_root)
    audio_downloader = AudioDownloader(cache_dir / "audio", cache_settings=audio_cache_settings)
    return CollectorOrchestrator(
        state_store=state_store,
        topic_router=topic_router,
        video_gateway=gateway,
        note_generator=note_generator,
        notes_root=notes_dir,
        transcripts_root=transcripts_dir,
        analysis_root=analysis_dir,
        audio_downloader=audio_downloader,
        stt_client=stt_client,
    )


def _handle_route_topic(args: argparse.Namespace, orchestrator: CollectorOrchestrator | None) -> None:
    orchestrator = _require_orchestrator(orchestrator)
    routed = orchestrator.route_topic(topic=args.topic, limit=args.limit)
    if args.json:
        print(json.dumps(routed, ensure_ascii=False, indent=2))
        return

    print(f"主題: {args.topic}")
    for item in routed:
        matched = ", ".join(item["matched_terms"]) if item["matched_terms"] else "(無明確命中)"
        print(f"- {item['channel']} | score={item['score']:.1f} | {matched}")
        print(f"  理由: {item['reason']}")


def _handle_collect_topic(args: argparse.Namespace, orchestrator: CollectorOrchestrator | None) -> None:
    orchestrator = _require_orchestrator(orchestrator)
    result = orchestrator.collect_from_topic(
        topic=args.topic,
        max_channels=args.max_channels,
        max_videos_per_channel=args.max_videos_per_channel,
        initial_video_limit=args.initial_video_limit,
        transcript_language=args.transcript_language,
        write_transcripts=not args.dry_run,
        initialize_analysis=not args.dry_run,
        write_notes=not args.dry_run,
        update_state=not args.dry_run,
    )

    if args.json:
        print(json.dumps(orchestrator.to_dict(result), ensure_ascii=False, indent=2))
        return

    print(f"主題: {result.topic}")
    for item in result.channel_results:
        print(f"- {item.channel.name} | {item.status} | {item.message}")
        if item.new_videos:
            print(f"  新影片: {', '.join(video.title for video in item.new_videos)}")
        if item.transcript_paths:
            print(f"  逐字稿: {', '.join(str(path) for path in item.transcript_paths)}")
        if item.analysis_paths:
            print(f"  分析: {', '.join(str(path) for path in item.analysis_paths)}")
        if item.note_paths:
            print(f"  筆記: {', '.join(str(path) for path in item.note_paths)}")


def _handle_export_transcripts(args: argparse.Namespace, orchestrator: CollectorOrchestrator | None) -> None:
    orchestrator = _require_orchestrator(orchestrator)
    result = orchestrator.collect_from_topic(
        topic=args.topic,
        max_channels=args.max_channels,
        max_videos_per_channel=args.max_videos_per_channel,
        initial_video_limit=args.initial_video_limit,
        transcript_language=args.transcript_language,
        write_transcripts=True,
        initialize_analysis=True,
        write_notes=False,
        update_state=not args.dry_run,
    )

    if args.json:
        print(json.dumps(orchestrator.to_dict(result), ensure_ascii=False, indent=2))
        return

    print(f"主題: {result.topic}")
    for item in result.channel_results:
        print(f"- {item.channel.name} | {item.status} | {item.message}")
        if item.transcript_paths:
            print(f"  逐字稿: {', '.join(str(path) for path in item.transcript_paths)}")
        if item.analysis_paths:
            print(f"  分析: {', '.join(str(path) for path in item.analysis_paths)}")


def _handle_list_tags(args: argparse.Namespace, orchestrator: CollectorOrchestrator | None) -> None:
    orchestrator = _require_orchestrator(orchestrator)
    tags = orchestrator.list_tags()
    if args.json:
        print(json.dumps(tags, ensure_ascii=False, indent=2))
        return
    print("=== 所有不重複標籤 ===")
    for tag in tags:
        print(f"- {tag}")


def _handle_list_channels(args: argparse.Namespace, orchestrator: CollectorOrchestrator | None) -> None:
    orchestrator = _require_orchestrator(orchestrator)
    channels = orchestrator.list_channels(
        watch_tier=args.watch_tier,
        include_paused=args.include_paused,
    )
    if args.json:
        print(json.dumps(channels, ensure_ascii=False, indent=2))
        return
    if args.watch_tier:
        title = f"=== {args.watch_tier} 頻道 ({len(channels)} 個) ==="
    else:
        title = f"=== 全部頻道 ({len(channels)} 個) ==="
    print(title)
    for item in channels:
        print(f"- {item['channel']} [{item['watch_tier']}] priority={item['priority']}: {item['url']}")


def _handle_get_channel_tags(args: argparse.Namespace, orchestrator: CollectorOrchestrator | None) -> None:
    orchestrator = _require_orchestrator(orchestrator)
    tags = orchestrator.get_channel_tags(args.channel)
    if tags is None:
        raise SystemExit(f"找不到頻道: {args.channel}")
    if args.json:
        print(json.dumps(tags, ensure_ascii=False, indent=2))
        return
    print(f"{args.channel} 標籤: {', '.join(tags)}")


def _handle_get_channels_by_tags(args: argparse.Namespace, orchestrator: CollectorOrchestrator | None) -> None:
    orchestrator = _require_orchestrator(orchestrator)
    result = orchestrator.get_channels_by_tags(args.tags, include_paused=args.include_paused)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(f"=== 包含標籤 {', '.join(args.tags)} 的頻道 ===")
    if not result:
        raise SystemExit("找不到符合的頻道")
    for tier in ["core", "normal", "optional", "paused"]:
        if tier not in result:
            continue
        print(f"\n[{tier} 頻道]")
        for item in result[tier]:
            print(f"- {item['channel']}: {item['url']}")


def _handle_get_last_checked(args: argparse.Namespace, orchestrator: CollectorOrchestrator | None) -> None:
    orchestrator = _require_orchestrator(orchestrator)
    title = orchestrator.get_last_checked_title(args.channel)
    if title is None:
        raise SystemExit(f"找不到頻道: {args.channel}")
    if args.json:
        print(json.dumps({"channel": args.channel, "last_checked_video_title": title}, ensure_ascii=False, indent=2))
        return
    print(f"{args.channel} 上次確認的影片: {title if title else '(尚未紀錄)'}")


def _handle_update_last_checked(args: argparse.Namespace, orchestrator: CollectorOrchestrator | None) -> None:
    orchestrator = _require_orchestrator(orchestrator)
    try:
        orchestrator.update_last_checked_title(args.channel, args.title)
    except KeyError:
        raise SystemExit(f"找不到頻道: {args.channel}") from None
    print(f"成功更新 {args.channel} 的最後確認影片為: '{args.title}'")


def _handle_check_stt(args: argparse.Namespace, orchestrator: CollectorOrchestrator | None) -> None:
    del orchestrator
    settings = load_stt_settings(Path.cwd())
    health = check_stt_provider(settings)
    payload = {
        "ok": health.ok,
        "provider": health.provider or None,
        "message": health.message,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    print(f"STT provider: {health.provider or '(未設定)'}")
    print(f"狀態: {'ok' if health.ok else 'not_ready'}")
    print(f"訊息: {health.message}")


def _handle_enrich_notes(args: argparse.Namespace, orchestrator: CollectorOrchestrator | None) -> None:
    del orchestrator
    provider = RssResearchProvider(feed_urls=args.rss_feed)
    enricher = ResearchNoteEnricher(provider)
    note_paths = _resolve_note_paths(
        notes_dir=_resolve_project_path(Path.cwd(), args.notes_dir),
        note_paths=args.note_paths,
        date_value=args.date,
    )
    results = enricher.enrich_notes(
        note_paths=note_paths,
        keywords=args.keywords,
        limit=args.limit,
    )

    if args.json:
        payload = [
            {
                "note_path": str(item.note_path),
                "note_title": item.note_title,
                "keywords": item.keywords,
                "evidence": [
                    {
                        "title": evidence.title,
                        "source": evidence.source,
                        "summary": evidence.summary,
                        "url": evidence.url,
                        "published_at": evidence.published_at,
                        "score": evidence.score,
                    }
                    for evidence in item.evidence
                ],
            }
            for item in results
        ]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    for result in results:
        output_path = write_enrichment_result(result)
        print(f"- {result.note_title} | 關鍵字: {', '.join(result.keywords) if result.keywords else '(無)'}")
        print(f"  研究輸出: {output_path}")
        print(f"  命中文章數: {len(result.evidence)}")


def _handle_prepare_analysis(args: argparse.Namespace, orchestrator: CollectorOrchestrator | None) -> None:
    del orchestrator
    transcript_artifact = read_transcript_artifact(args.transcript_path)
    store = AnalysisArtifactStore()
    if args.output_path:
        artifact = store.initialize_pending_at_path(transcript_artifact, args.output_path)
    else:
        artifact = store.initialize_pending(
            transcript_artifact=transcript_artifact,
            output_root=_resolve_project_path(Path.cwd(), args.analysis_dir),
        )

    if args.json:
        print(artifact.path.read_text(encoding="utf-8"))
        return

    print(f"已初始化 analysis artifact: {artifact.path}")
    print("下一步：把 transcript artifact 與 analysis artifact 路徑交給 `transcript-analyst` 子 Agent；若使用 Codex，請明確要求它 spawn `transcript-analyst`，若使用 Gemini CLI，則可直接用 `@transcript-analyst`。")


def _handle_render_note(args: argparse.Namespace, orchestrator: CollectorOrchestrator | None) -> None:
    del orchestrator
    transcript_artifact = read_transcript_artifact(args.transcript_path)
    channel, video, transcript = artifact_to_note_context_data(transcript_artifact)
    note_generator = MarkdownNoteGenerator()
    analysis_artifact = None
    if args.analysis_path:
        analysis_artifact = AnalysisArtifactStore().read(args.analysis_path)

    note = note_generator.write_note(
        context=NoteContext(
            topic=transcript_artifact.topic,
            channel=channel,
            video=video,
            transcript=transcript,
            analysis_artifact=analysis_artifact,
        ),
        output_root=_resolve_project_path(Path.cwd(), args.notes_dir),
        output_date=_resolve_collected_date(transcript_artifact.collected_date),
    )

    if args.json:
        print(json.dumps({"note_path": str(note.path), "content": note.content}, ensure_ascii=False, indent=2))
        return

    print(f"已產出筆記: {note.path}")


def _handle_synthesize_answer(args: argparse.Namespace, orchestrator: CollectorOrchestrator | None) -> None:
    del orchestrator
    artifact = ResearchArtifactStore().read(args.research_artifact_path)
    store = ResearchAnswerStore()
    output_path = Path(args.output_path) if args.output_path else store.build_path(
        artifact=artifact,
        output_root=_resolve_project_path(Path.cwd(), args.analysis_dir),
    )
    answer = ResearchAnswerBuilder().build_stub(
        question=args.question,
        artifact=artifact,
        output_path=output_path,
    )
    store.write(answer)

    if args.json:
        print(answer.path.read_text(encoding="utf-8"))
        return

    print(render_research_answer(answer))
    print("")
    print(f"research answer: {answer.path}")
    print("下一步：將 research artifact 與這份 answer 交給 `research-answer-synthesizer` 子 Agent；若使用 Codex，請明確要求它 spawn `research-answer-synthesizer`，若使用 Gemini CLI，則可直接用 `@research-answer-synthesizer`。它負責 relevant claim selection，以及 direct mention / inference / needs validation 的主要判斷；Python / CLI 這裡只負責準備 output path、answer JSON 與後續 rendering。")


def _handle_analyze_prediction_market(args: argparse.Namespace, orchestrator: CollectorOrchestrator | None) -> None:
    del orchestrator
    answer = ResearchAnswerStore().read(args.research_answer_path)
    routing = OpportunityRouter().route(answer)
    result = PredictionMarketAnalyzer().analyze(answer, routing)

    payload = {
        "research_answer_path": str(result.research_answer_path),
        "route": result.route,
        "status": result.status,
        "summary": result.summary,
        "candidates": [
            {
                "framing": candidate.framing,
                "search_queries": candidate.search_queries,
                "rationale": candidate.rationale,
                "source_claims": candidate.source_claims,
                "warnings": candidate.warnings,
            }
            for candidate in result.candidates
        ],
        "warnings": result.warnings,
    }

    if args.output_path:
        output_path = Path(args.output_path)
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    print(render_prediction_market_analysis(result))
    if args.output_path:
        print("")
        print(f"prediction market analysis: {args.output_path}")


def _resolve_project_path(project_root: Path, target: str) -> Path:
    target_path = Path(target)
    if target_path.is_absolute():
        return target_path
    return project_root / target_path


def _resolve_note_paths(notes_dir: Path, note_paths: list[str] | None, date_value: str | None) -> list[Path]:
    if note_paths:
        return [Path(path) for path in note_paths]

    target_dir = notes_dir / date_value if date_value else notes_dir
    return sorted(target_dir.glob("**/*.md"))


def _require_orchestrator(orchestrator: CollectorOrchestrator | None) -> CollectorOrchestrator:
    if orchestrator is None:
        raise RuntimeError("此命令需要 orchestrator")
    return orchestrator


def _resolve_collected_date(value: str) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)
