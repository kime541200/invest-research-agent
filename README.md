# info-collector

這個專案用來打造一個以主題驅動的 YouTube 資訊蒐集 Agent。

目前主流程已聚焦在這條可重跑的 pipeline：

1. 使用者輸入想討論的主題
2. 系統根據 `resources.yaml` 的 `tags`、`alias`、`topic_keywords` 推薦頻道
3. 透過 `yt-mcp-server` 抓取候選頻道的最新影片與字幕
4. 將字幕整理成較適合 Agent 消化的內容
5. 產出標準化 Markdown 筆記到 `notes/YYYY-MM-DD/`
6. 更新 `resources.yaml` 的 `last_checked_video_title`，避免重複處理

`NotebookLM` 目前不是核心成功路徑的一部分，後續會以獨立 grounding gateway 的方式接入。

## 快速開始

如果你只想先把專案跑起來，建議照這個順序：

1. 初始化 submodules
2. 設定並啟動 `yt-mcp-server`
3. 準備 `resources.yaml`
4. 安裝根專案
5. 用 `python -m info_collector ...` 執行正式流程

```bash
git submodule update --init --recursive
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
python -m info_collector route-topic --topic "AI 新創與科技商業趨勢"
```

在開始前，建議先看：

- 共通前置條件：`docs/pre-required.md`
- Cursor MCP 設定：`docs/mcp-config/cursor.md`
- Gemini MCP 設定：`docs/mcp-config/gemini.md`
- Claude MCP 設定：`docs/mcp-config/claude.md`
- 透過 MCPorter 訪問 MCP：`docs/mcp-config/mcporter.md`

## 專案結構

```text
.
├── AGENTS.md
├── config/
│   └── mcporter.json
├── docs/
│   └── mcp-config/
├── modules/
│   ├── notebooklm-skill/
│   └── yt-mcp-server/
├── notes/
├── pyproject.toml
├── resources.example.yaml
├── resources.yaml
├── src/
│   └── info_collector/
└── tests/
```

## 先決條件

- 已抓下子模組
- `yt-mcp-server` 已正確啟動並可由 `http://localhost:8088/mcp` 存取
- 專案根目錄存在 `resources.yaml`
- `modules/yt-mcp-server/.env` 內有可用的 `YOUTUBE_API_KEY`

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

## MCP 存取方式

本專案目前支援多種 MCP 存取方式，文件已拆開管理：

- Cursor：看 `docs/mcp-config/cursor.md`
- Gemini：看 `docs/mcp-config/gemini.md`
- Claude：看 `docs/mcp-config/claude.md`
- MCPorter：看 `docs/mcp-config/mcporter.md`

如果你只想快速驗證 `yt-mcp-server`，`mcporter` 通常是最直接的方式。

本專案已提供：

- `config/mcporter.json`

所以在專案根目錄可以直接執行：

```bash
npx mcporter list
npx mcporter list yt-mcp-server --schema
npx mcporter call yt-mcp-server.transcripts_getTranscript video_id=7U1qyLstvBU --output json
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

## 正式 CLI 入口

根專案現在唯一正式入口是：

```bash
python -m info_collector ...
```

常用命令如下。

列出所有 tags：

```bash
source .venv/bin/activate
python -m info_collector list-tags
```

列出所有頻道：

```bash
source .venv/bin/activate
python -m info_collector list-channels
```

只列出 `always_watch` 頻道：

```bash
source .venv/bin/activate
python -m info_collector list-channels --always-watch
```

查詢某個頻道的 tags：

```bash
source .venv/bin/activate
python -m info_collector get-channel-tags --channel inside6202
```

依 tags 查詢頻道：

```bash
source .venv/bin/activate
python -m info_collector get-channels-by-tags --tags AI 科技
```

查看或更新最後確認影片：

```bash
source .venv/bin/activate
python -m info_collector get-last-checked --channel inside6202
python -m info_collector update-last-checked --channel inside6202 --title "新影片標題"
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

## 範例工作流

下面是一個從主題輸入到正式收集的最小工作流。

1. 先看主題會命中哪些頻道：

```bash
source .venv/bin/activate
python -m info_collector route-topic --topic "AI 新創與科技商業趨勢"
```

2. 如果想先確認候選頻道，也可以直接查 tags：

```bash
source .venv/bin/activate
python -m info_collector get-channels-by-tags --tags AI 科技 商業
```

3. 先用 dry-run 驗證整條流程是否能抓到新影片：

```bash
source .venv/bin/activate
python -m info_collector collect-from-topic \
  --topic "AI 新創與科技商業趨勢" \
  --max-channels 2 \
  --dry-run
```

4. 確認結果合理後，再正式寫入筆記與更新狀態：

```bash
source .venv/bin/activate
python -m info_collector collect-from-topic \
  --topic "AI 新創與科技商業趨勢" \
  --max-channels 2 \
  --max-videos-per-channel 3 \
  --transcript-language zh-TW
```

5. 若要確認某個頻道目前記錄到哪支影片：

```bash
source .venv/bin/activate
python -m info_collector get-last-checked --channel inside6202
```

完成後，新的 Markdown 筆記會寫到：

```text
notes/YYYY-MM-DD/
```

## 目前狀態

目前專案已具備：

- `tag-first` 頻道路由
- `yt-mcp-server` 字幕抓取與結構化回傳
- 合併後字幕 `merged_transcript`
- 筆記生成時優先使用合併後字幕
- 以 `mcporter` 直接訪問 MCP server 的能力

目前尚未完成或仍在後續階段的部分：

- NotebookLM ingestion 自動化
- 更強的 grounding workflow
- 更完整的摘要與對話式分析能力

## 測試

```bash
source .venv/bin/activate
pytest
```