from __future__ import annotations

import argparse
import json
from pathlib import Path

from info_collector.audio_downloader import AudioDownloader, load_audio_cache_settings
from info_collector.mcp_client import McpHttpClient
from info_collector.note_generator import MarkdownNoteGenerator
from info_collector.orchestrator import CollectorOrchestrator
from info_collector.state_store import ResourceStateStore
from info_collector.stt import SttClient, check_stt_provider, load_stt_settings
from info_collector.topic_router import TopicRouter
from info_collector.video_fetcher import YouTubeMcpGateway


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    if not hasattr(args, "handler"):
        parser.print_help()
        return

    orchestrator = _build_orchestrator(args)
    args.handler(args, orchestrator)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Topic-driven YouTube info collector")
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
        default=".cache/info-collector",
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
    check_stt.set_defaults(handler=_handle_check_stt)

    return parser


def _build_orchestrator(args: argparse.Namespace) -> CollectorOrchestrator:
    project_root = Path.cwd()
    resources_file = _resolve_project_path(project_root, args.resources_file)
    notes_dir = _resolve_project_path(project_root, args.notes_dir)
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
        audio_downloader=audio_downloader,
        stt_client=stt_client,
    )


def _handle_route_topic(args: argparse.Namespace, orchestrator: CollectorOrchestrator) -> None:
    routed = orchestrator.route_topic(topic=args.topic, limit=args.limit)
    if args.json:
        print(json.dumps(routed, ensure_ascii=False, indent=2))
        return

    print(f"主題: {args.topic}")
    for item in routed:
        matched = ", ".join(item["matched_terms"]) if item["matched_terms"] else "(無明確命中)"
        print(f"- {item['channel']} | score={item['score']:.1f} | {matched}")
        print(f"  理由: {item['reason']}")


def _handle_collect_topic(args: argparse.Namespace, orchestrator: CollectorOrchestrator) -> None:
    result = orchestrator.collect_from_topic(
        topic=args.topic,
        max_channels=args.max_channels,
        max_videos_per_channel=args.max_videos_per_channel,
        initial_video_limit=args.initial_video_limit,
        transcript_language=args.transcript_language,
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
        if item.note_paths:
            print(f"  筆記: {', '.join(str(path) for path in item.note_paths)}")


def _handle_list_tags(args: argparse.Namespace, orchestrator: CollectorOrchestrator) -> None:
    tags = orchestrator.list_tags()
    if args.json:
        print(json.dumps(tags, ensure_ascii=False, indent=2))
        return
    print("=== 所有不重複標籤 ===")
    for tag in tags:
        print(f"- {tag}")


def _handle_list_channels(args: argparse.Namespace, orchestrator: CollectorOrchestrator) -> None:
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


def _handle_get_channel_tags(args: argparse.Namespace, orchestrator: CollectorOrchestrator) -> None:
    tags = orchestrator.get_channel_tags(args.channel)
    if tags is None:
        raise SystemExit(f"找不到頻道: {args.channel}")
    if args.json:
        print(json.dumps(tags, ensure_ascii=False, indent=2))
        return
    print(f"{args.channel} 標籤: {', '.join(tags)}")


def _handle_get_channels_by_tags(args: argparse.Namespace, orchestrator: CollectorOrchestrator) -> None:
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


def _handle_get_last_checked(args: argparse.Namespace, orchestrator: CollectorOrchestrator) -> None:
    title = orchestrator.get_last_checked_title(args.channel)
    if title is None:
        raise SystemExit(f"找不到頻道: {args.channel}")
    if args.json:
        print(json.dumps({"channel": args.channel, "last_checked_video_title": title}, ensure_ascii=False, indent=2))
        return
    print(f"{args.channel} 上次確認的影片: {title if title else '(尚未紀錄)'}")


def _handle_update_last_checked(args: argparse.Namespace, orchestrator: CollectorOrchestrator) -> None:
    try:
        orchestrator.update_last_checked_title(args.channel, args.title)
    except KeyError:
        raise SystemExit(f"找不到頻道: {args.channel}") from None
    print(f"成功更新 {args.channel} 的最後確認影片為: '{args.title}'")


def _handle_check_stt(args: argparse.Namespace, orchestrator: CollectorOrchestrator) -> None:
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


def _resolve_project_path(project_root: Path, target: str) -> Path:
    target_path = Path(target)
    if target_path.is_absolute():
        return target_path
    return project_root / target_path
