from __future__ import annotations

import argparse
import json
from pathlib import Path

from info_collector.mcp_client import McpHttpClient
from info_collector.note_generator import MarkdownNoteGenerator
from info_collector.orchestrator import CollectorOrchestrator
from info_collector.state_store import ResourceStateStore
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

    return parser


def _build_orchestrator(args: argparse.Namespace) -> CollectorOrchestrator:
    project_root = Path.cwd()
    resources_file = _resolve_project_path(project_root, args.resources_file)
    notes_dir = _resolve_project_path(project_root, args.notes_dir)

    state_store = ResourceStateStore(resources_file)
    topic_router = TopicRouter()
    client = McpHttpClient(endpoint=args.mcp_url, timeout=args.timeout)
    gateway = YouTubeMcpGateway(client)
    note_generator = MarkdownNoteGenerator()
    return CollectorOrchestrator(
        state_store=state_store,
        topic_router=topic_router,
        video_gateway=gateway,
        note_generator=note_generator,
        notes_root=notes_dir,
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


def _resolve_project_path(project_root: Path, target: str) -> Path:
    target_path = Path(target)
    if target_path.is_absolute():
        return target_path
    return project_root / target_path
