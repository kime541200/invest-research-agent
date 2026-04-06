import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("錯誤: 尚未安裝 PyYAML。請執行 `pip install pyyaml` 安裝套件。", file=sys.stderr)
    sys.exit(1)

def _load_yaml(file_path: Path) -> dict:
    """內部同步方法：載入 YAML 檔案"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"讀取 YAML 檔案時發生錯誤: {e}", file=sys.stderr)
        sys.exit(1)

def main():
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
    
    # 自動定位 resources.yaml: 優先找專案根目錄
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    
    target_path = Path(args.file)
    if not target_path.is_absolute() and target_path.parent == Path('.'):
        target_path = project_root / args.file
        
    if not target_path.exists():
        print(f"找不到檔案: {target_path}", file=sys.stderr)
        sys.exit(1)

    data = _load_yaml(target_path)
    yt_channels = data.get("yt_channels", {})

    if args.list_always_watch:
        print("=== 必看頻道 ===")
        for name, info in yt_channels.items():
            if info.get("always_watch"):
                print(f"- {name}: {info.get('url')}")
    elif args.get_tags:
        channel = yt_channels.get(args.get_tags)
        if channel:
            tags = channel.get("tags", [])
            print(f"{args.get_tags} 標籤: {', '.join(tags)}")
        else:
            print(f"找不到頻道: {args.get_tags}", file=sys.stderr)
    elif args.get_all_tags:
        all_tags = set()
        for info in yt_channels.values():
            all_tags.update(info.get("tags", []))
        print("=== 所有不重複標籤 ===")
        for tag in sorted(all_tags):
            print(f"- {tag}")
    elif args.get_channels_by_tags:
        target_tags = set(args.get_channels_by_tags)
        print(f"=== 包含標籤 {', '.join(target_tags)} 的頻道 ===")
        always_watch = []
        optional_watch = []
        
        for name, info in yt_channels.items():
            channel_tags = set(info.get("tags", []))
            if target_tags.intersection(channel_tags):
                if info.get("always_watch"):
                    always_watch.append(name)
                else:
                    optional_watch.append(name)
                    
        if not always_watch and not optional_watch:
            print("找不到符合的頻道", file=sys.stderr)
        else:
            if always_watch:
                print("\n[必看頻道 - always_watch: true]")
                for name in always_watch:
                    print(f"- {name}: {yt_channels[name].get('url')}")
            if optional_watch:
                print("\n[選看頻道 - always_watch: false]")
                for name in optional_watch:
                    print(f"- {name}: {yt_channels[name].get('url')}")
    elif args.get_last_checked_title:
        channel = yt_channels.get(args.get_last_checked_title)
        if channel:
            title = channel.get("last_checked_video_title", "")
            print(f"{args.get_last_checked_title} 上次確認的影片: {title if title else '(尚未紀錄)'}")
        else:
            print(f"找不到頻道: {args.get_last_checked_title}", file=sys.stderr)
    elif args.update_last_checked_title:
        channel_name, new_title = args.update_last_checked_title
        if channel_name in yt_channels:
            yt_channels[channel_name]["last_checked_video_title"] = new_title
            try:
                with open(target_path, 'w', encoding='utf-8') as f:
                    yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
                print(f"成功更新 {channel_name} 的最後確認影片為: '{new_title}'")
            except Exception as e:
                print(f"寫入 YAML 檔案時發生錯誤: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            print(f"找不到頻道: {channel_name}", file=sys.stderr)
    elif args.list_all:
        print(f"=== 全部頻道 ({len(yt_channels)} 個) ===")
        for name, info in yt_channels.items():
            print(f"- {name}: {info.get('url')}")
    else:
        # 若無帶參數，顯示預設的精要資訊
        print(f"總共讀取了 {len(yt_channels)} 個頻道，包含:")
        print(f"  必看頻道: {sum(1 for c in yt_channels.values() if c.get('always_watch'))} 個")
        print("\n使用 `--help` 獲取更多 CLI 操作指令。")

if __name__ == "__main__":
    main()
