# info-collector

這個專案用來打造一個以主題驅動的 YouTube 資訊蒐集 Agent。第一階段先聚焦在穩定的主流程：

1. 使用者輸入想討論的主題
2. 系統根據 `resources.yaml` 的 `tags`、`alias`、`topic_keywords` 推薦頻道
3. 透過 `yt-mcp-server` 抓取候選頻道的最新影片與字幕
4. 產出標準化 Markdown 筆記到 `notes/YYYY-MM-DD/`
5. 更新 `resources.yaml` 的 `last_checked_video_title` 避免重複處理

`NotebookLM` 目前不在核心成功路徑內，後續會以獨立 grounding gateway 的方式接入。

## 專案結構

```text
.
├── AGENTS.md
├── docs/
├── modules/
│   ├── notebooklm-skill/
│   └── yt-mcp-server/
├── notes/
├── pyproject.toml
├── resources.example.yaml
├── resources.yaml
├── scripts/
│   └── load_scripts.py
├── src/
│   └── info_collector/
└── tests/
```

## 先決條件

- 已抓下子模組
- `yt-mcp-server` 已正確啟動並可由 `http://localhost:8088/mcp` 存取
- 專案根目錄存在 `resources.yaml`

如果還沒初始化子模組：

```bash
git submodule update --init --recursive
```

## 安裝

這個專案使用 `uv` 與 `src-layout`。

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

## `resources.yaml` 結構

`yt_channels.<channel_name>` 目前支援以下欄位：

- `url`: 頻道網址
- `last_checked_video_title`: 上次成功處理的最新影片標題
- `alias`: 頻道別名
- `tags`: 基礎主題標籤
- `topic_keywords`: 更細的路由關鍵詞
- `description`: 頻道內容描述
- `priority`: 命中後的排序加權
- `channel_id`: 快取過的 YouTube channel id，可留空
- `always_watch`: 命中主題時提高優先度

可參考 `resources.example.yaml`。

## CLI

列出所有 tags：

```bash
source .venv/bin/activate
python -m info_collector list-tags
```

根據主題先看推薦頻道：

```bash
source .venv/bin/activate
python -m info_collector route-topic --topic "AI 新創與科技商業趨勢"
```

實際執行收集流程：

```bash
source .venv/bin/activate
python -m info_collector collect-from-topic \
  --topic "AI 新創與科技商業趨勢" \
  --max-channels 3 \
  --max-videos-per-channel 5 \
  --transcript-language zh-TW
```

若只想驗證 routing 與 yt-mcp-server 連線，不寫入任何筆記或狀態：

```bash
source .venv/bin/activate
python -m info_collector collect-from-topic \
  --topic "美股與資產配置" \
  --dry-run
```

## 舊腳本相容性

`scripts/load_scripts.py` 仍可使用，並已改成新的 `state_store` 相容層，適合做：

- 查 tags
- 查頻道
- 查 `last_checked_video_title`
- 手動更新 `last_checked_video_title`

## 測試

```bash
source .venv/bin/activate
pytest
```