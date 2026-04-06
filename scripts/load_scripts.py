from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from info_collector.state_store import ResourceStateStore


def main() -> None:
    parser = argparse.ArgumentParser(description="讀取 resources.yaml 的內容")
    parser.add_argument("--file", type=str, default="resources.yaml", help="指定 resources.yaml 的路徑 (預設為專案根目錄)")
    parser.add_argument("--list-all", action="store_true", help="列出所有的頻道與 URL")
    parser.add_argument("--list-always-watch", action="store_true", help="列出 always_watch 為 true 的頻道")
    parser.add_argument("--get-tags", type=str, metavar="CHANNEL", help="獲取指定頻道的 tags")
    parser.add_argument("--get-all-tags", action="store_true", help="獲取所有頻道中不重複的 tags")
    parser.add_argument("--get-channels-by-tags", type=str, nargs="+", metavar="TAG", help="輸入一個或多個標籤以獲取包含標籤的頻道連結")
    parser.add_argument("--get-last-checked-title", type=str, metavar="CHANNEL", help="獲取指定頻道上一次確認的影片標題")
    parser.add_argument("--update-last-checked-title", nargs=2, metavar=("CHANNEL", "TITLE"), help="更新指定頻道的最後確認影片標題")
    
    args = parser.parse_args()

    target_path = Path(args.file)
    if not target_path.is_absolute() and target_path.parent == Path('.'):
        target_path = PROJECT_ROOT / args.file

    if not target_path.exists():
        print(f"找不到檔案: {target_path}", file=sys.stderr)
        sys.exit(1)

    store = ResourceStateStore(target_path)
    channels = store.get_channels()
    channel_by_name = {channel.name: channel for channel in channels}

    if args.list_always_watch:
        print("=== 必看頻道 ===")
        for channel in channels:
            if channel.always_watch:
                print(f"- {channel.name}: {channel.url}")
    elif args.get_tags:
        channel = channel_by_name.get(args.get_tags)
        if channel:
            print(f"{args.get_tags} 標籤: {', '.join(channel.tags)}")
        else:
            print(f"找不到頻道: {args.get_tags}", file=sys.stderr)
    elif args.get_all_tags:
        print("=== 所有不重複標籤 ===")
        for tag in store.get_all_tags():
            print(f"- {tag}")
    elif args.get_channels_by_tags:
        target_tags = args.get_channels_by_tags
        print(f"=== 包含標籤 {', '.join(target_tags)} 的頻道 ===")
        always_watch, optional_watch = store.get_channels_by_tags(target_tags)

        if not always_watch and not optional_watch:
            print("找不到符合的頻道", file=sys.stderr)
        else:
            if always_watch:
                print("\n[必看頻道 - always_watch: true]")
                for channel in always_watch:
                    print(f"- {channel.name}: {channel.url}")
            if optional_watch:
                print("\n[選看頻道 - always_watch: false]")
                for channel in optional_watch:
                    print(f"- {channel.name}: {channel.url}")
    elif args.get_last_checked_title:
        channel = channel_by_name.get(args.get_last_checked_title)
        if channel:
            title = channel.last_checked_video_title
            print(f"{args.get_last_checked_title} 上次確認的影片: {title if title else '(尚未紀錄)'}")
        else:
            print(f"找不到頻道: {args.get_last_checked_title}", file=sys.stderr)
    elif args.update_last_checked_title:
        channel_name, new_title = args.update_last_checked_title
        if channel_name not in channel_by_name:
            print(f"找不到頻道: {channel_name}", file=sys.stderr)
            sys.exit(1)
        try:
            store.update_last_checked_title(channel_name, new_title)
            print(f"成功更新 {channel_name} 的最後確認影片為: '{new_title}'")
        except Exception as exc:
            print(f"寫入 YAML 檔案時發生錯誤: {exc}", file=sys.stderr)
            sys.exit(1)
    elif args.list_all:
        print(f"=== 全部頻道 ({len(channels)} 個) ===")
        for channel in channels:
            print(f"- {channel.name}: {channel.url}")
    else:
        # 若無帶參數，顯示預設的精要資訊
        print(f"總共讀取了 {len(channels)} 個頻道，包含:")
        print(f"  必看頻道: {sum(1 for channel in channels if channel.always_watch)} 個")
        print("\n使用 `--help` 獲取更多 CLI 操作指令。")


if __name__ == "__main__":
    main()
