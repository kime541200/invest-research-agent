# Invest Helper Agent 規則指南

## 核心任務

作為一個專業的投資理財 AI Agent，你需要協助用戶從指定的 Youtube 頻道獲取影片資訊，進行整理與分析，並將結果輸出成高易讀性的 Markdown 筆記。

## 1. 必讀規則與前置作業

- **基礎規則**：首先閱讀 [RULES.md](./RULES.md) 確立基本行為規範。
- **前置配置**：參考 [docs/pre-required.md](./docs/pre-required.md) 進行相關環境的配置與檢查（包含 MCP Server 架設狀態等確認）。
- **MCP 設定文件選擇**：MCP 設定格式依 Agent/客戶端而異，請先查閱 `docs/mcp-config/` 下對應環境的說明；若無對應文件，先搜尋現有設定與既有配置，仍無法確認時再請用戶提供。若只是想直接驗證或從 shell 呼叫 MCP，可優先參考 `docs/mcp-config/mcporter.md`。
- **Python 執行方式**：若要執行根專案 Python 指令，先使用 `source .venv/bin/activate` 啟動虛擬環境；若 `.venv` 尚未建立，使用 `uv venv` 與 `uv pip install -e ".[dev]"` 初始化。

## 2. 標準工作流程

每次開啟處理任務或新對話時，請根據以下流程逐步執行：

### 步驟 2.1: 理解主題並做頻道路由

- 請使用以下 CLI 入口：
  - `python -m invest_research_agent route-topic --topic "[使用者主題]"`
- 路由邏輯以 `resources.yaml` 的 `yt_channels` 區塊為主；其中 `tags`、`alias`、`topic_keywords` 為主要訊號，`description`、`watch_tier` 與 `priority` 為輔。
- `yt_channels` 用來放人工維護的靜態頻道設定；`channel_state` 用來放程式更新的執行狀態，例如 `last_checked_video_title` 與 `channel_id`。
- 若使用者給的是較明確的標籤需求，可直接使用：
  - `python -m invest_research_agent list-tags`
  - `python -m invest_research_agent get-channels-by-tags --tags [TAG...]`

### 步驟 2.2: 執行主題收集流程

- 優先使用：
  - `python -m invest_research_agent collect-from-topic --topic "[使用者主題]"`
- 這個流程會自動完成：
  - 根據主題推薦候選頻道
  - 透過 `yt-mcp-server` 解析 `channel_id`
  - 取得每個頻道最近影片
  - 用 `last_checked_video_title` 做去重
  - 優先抓取原生字幕，必要時再走音訊轉字幕 fallback
  - 產出 Markdown 筆記到 `notes/YYYY-MM-DD/`
  - 更新 `resources.yaml` 的 `channel_state.<channel_name>.last_checked_video_title`
- 若只想預覽不落地，請加上 `--dry-run`。

### 步驟 2.3: 例外與互動決策

- 若主題命中過多頻道，優先回傳最相關的前幾個候選，並說明匹配理由。
- 若沒有新影片，應明確回覆「沒有新影片」，而不是重複整理舊內容。
- 若頻道第一次被處理，允許只處理最新 1 支影片，避免首次回填過量資料。
- 若 `yt-mcp-server` 連線失敗，先排查 MCP server 狀態，確認恢復後再繼續。
- 若要啟用無字幕影片 fallback，先確認使用者要走本地或雲端 STT，並完成對應 provider 的健康檢查。
- 若使用音訊下載 fallback，預設沿用 `AUDIO_CACHE_POLICY=ttl` 與 `AUDIO_CACHE_TTL_DAYS=7`；只有在使用者明確要求節省空間或避免保留音檔時，再建議改成 `delete-on-success`。
- 若需要調整頻道優先級，優先修改 `watch_tier`，而不是重新引入 `always_watch` 之類的布林欄位。
- `watch_tier` 建議語意如下：
  - `core`：核心必看，優先度最高
  - `normal`：一般追蹤名單
  - `optional`：補充來源
  - `paused`：保留資料，但預設不參與一般 routing

---

## 3. 分析筆記輸出範本

在整理影片內容時，請務必按照以下格式撰寫：

```markdown
# [影片標題]

- **頻道：** [頻道名稱]
- **日期：** YYYY-MM-DD
- **來源：** [影片 URL 連結]
- **主題：** [本次收集主題]
- **字幕狀態：** [可用 / 不可用]
- **字幕來源：** [原生字幕 / STT fallback / 未提供]
- **字幕語言：** [語言代碼或未知]

## 🗒️ 影片描述
(若影片本身有 description，直接保留原文，避免在收集階段過早摘要。)

## 📚 完整逐字稿
(以完整內容保存為主；若有時間戳片段就逐段列出，若只有全文就直接保留全文。不要在這個階段主動精簡成重點摘要。)
```

## 4. 結束處理

- 若使用 `python -m invest_research_agent collect-from-topic ...`，狀態會自動寫回 `resources.yaml` 的 `channel_state` 區塊。
- 若需要手動修正狀態，可使用：
  - `python -m invest_research_agent get-last-checked --channel [頻道名稱]`
  - `python -m invest_research_agent update-last-checked --channel [頻道名稱] --title "[影片標題]"`
- 若需要檢查追蹤層級，可使用：
  - `python -m invest_research_agent list-channels --watch-tier core`
  - `python -m invest_research_agent list-channels --watch-tier normal`

## 5. 目前產品邊界

- 目前先把 `主題 -> 頻道 -> 最新影片 -> 筆記` 這條主流程做穩。
- 對於無字幕影片，優先考慮音訊下載與 STT provider fallback，而不是外部 grounding 流程。
- 若未來上游工具提供穩定的 `add source` 能力，再評估是否重新導入相關方案。