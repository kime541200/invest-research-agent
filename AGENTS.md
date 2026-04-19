# Invest Helper Agent 規則指南

## 核心任務

作為一個專業的投資理財 AI Agent，你需要協助用戶從指定的 Youtube 頻道獲取影片資訊，進行整理與分析，並將結果輸出成高易讀性的 Markdown 筆記。

## 專案核心定位（最高優先）

這個專案的核心目標，不是另外做出一個獨立的 agent 產品，而是：

- 利用 Claude Code、Gemini CLI 等既有 coding agent 框架的能力
- 配置一套適合投資研究與賺錢機會探索的 workspace / workflow
- 讓 agent 能在這個專案中更自然地使用 artifacts、subagents、commands、skills 與既有資料來源

因此在做設計與實作時，必須優先遵守以下原則：

- **agent workflow 優先於 Python feature expansion**：先思考這項能力是否應由 subagent、skill、artifact contract 或 command workflow 承接，而不是先做成新的 Python 產品功能。
- **Python / CLI / artifacts 是支撐層，不是主角**：它們的責任是提供穩定的 research intermediate、驗證入口與可重跑流程，讓 coding agent 更容易做對事。
- **避免持續滑向獨立 agent 產品**：若某項能力主要是在擴張本地 runtime、包裝自己的 agent 行為、或讓 Python 成為主要智能層，應先停下來重新檢查是否偏離專案方向。
- **subagent / skill / workflow 的責任邊界要清楚**：讓現成 coding agent 框架能根據 repo 內的設定，自然調度正確的專責能力。

每當要新增新能力時，請先問自己：

1. 這項能力是不是更適合做成 subagent / skill / command workflow？
2. 這項能力是否正在把 repo 推向一個獨立 agent app？
3. 這項能力是否真的有幫助現成 coding agent 框架更好地完成投資研究任務？

## 1. 必讀規則與前置作業

- **基礎規則**：首先閱讀 [RULES.md](./RULES.md) 確立基本行為規範。
- **前置配置**：參考 [docs/pre-required.md](./docs/pre-required.md) 進行相關環境的配置與檢查（包含 MCP Server 架設狀態等確認）。
- **MCP 設定文件選擇**：MCP 設定格式依 Agent/客戶端而異，請先查閱 `docs/mcp-config/` 下對應環境的說明；若無對應文件，先搜尋現有設定與既有配置，仍無法確認時再請用戶提供。若只是想直接驗證或從 shell 呼叫 MCP，可優先參考 `docs/mcp-config/mcporter.md`。
- **Python 執行方式**：若要執行根專案 Python 指令，先使用 `source .venv/bin/activate` 啟動虛擬環境；若 `.venv` 尚未建立，使用 `uv venv` 與 `uv pip install -e ".[dev]"` 初始化。
- **Gemini CLI 測試方式**：若需要做真實 workflow 驗證或 cross-check，可直接使用 `gemini` 啟動 Gemini CLI；可用 `gemini -p "<prompt>"` 直接送提示詞，若希望測試流程中不要停下來逐步確認，可使用 `gemini --yolo`。需要查看更多操作時，優先用 `gemini --help`；若需要查官方說明或 repo 脈絡，可透過 `/gh-cli` 查看 `google-gemini/gemini-cli`。

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
  - 產出 Markdown 筆記到 `notes/YYYY-MM-DD/<topic>/`
  - 更新 `resources.yaml` 的 `channel_state.<channel_name>.last_checked_video_title`
- 若只想預覽不落地，請加上 `--dry-run`。

### 步驟 2.2.1: 逐字稿與分析分層

- 完整逐字稿取得後，應優先保存為獨立 transcript artifact，而不是只把內容埋進最終筆記。
- transcript artifact 是事實層輸入；analysis artifact 是整理與推理層輸出；最終 note 則是展示與閱讀層。
- 主 Agent 應負責：
  - 擷取影片與字幕
  - 保存 transcript artifact
  - 準備 analysis artifact
  - 整合最終 note
- 主 Agent 不應直接根據長逐字稿產出研究報告內容；當 transcript artifact 已存在時，應優先委派給 `transcript-analyst` 子 Agent。Gemini 定義位於 `.gemini/agents/transcript-analyst.md`；Codex 定義位於 `.codex/agents/transcript-analyst.toml`。
- `transcript-analyst` 子 Agent 只負責：
  - 讀取 transcript artifact
  - 產出 analysis artifact
  - 提煉 `核心結論`、`重點拆解`、`重要依據`、`限制條件`、`後續追蹤`
- `transcript-analyst` 不負責：
  - 重新抓影片或字幕
  - 修改 `resources.yaml`
  - 做外部 research enrichment
  - 直接寫最終 note
- 若 analysis artifact 尚未完成，最終 note 應明確標示分析尚未產出，而不是用逐字稿開頭幾句硬填摘要。

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
- 若要分步驗證 transcript -> analysis -> note 流程，可依序使用：
  - `python -m invest_research_agent export-transcripts-from-topic --topic "[使用者主題]"`
  - `python -m invest_research_agent prepare-analysis --transcript-path "[transcript artifact path]"`
  - 使用 `transcript-analyst` 子 Agent 完成 analysis artifact；若在 Gemini CLI 可用 `@transcript-analyst`，若在 Codex 則明確要求 spawn `transcript-analyst`
  - `python -m invest_research_agent render-note --transcript-path "[transcript artifact path]" --analysis-path "[analysis artifact path]"`
- 若需要手動修正狀態，可使用：
  - `python -m invest_research_agent get-last-checked --channel [頻道名稱]`
  - `python -m invest_research_agent update-last-checked --channel [頻道名稱] --title "[影片標題]"`
- 若需要檢查追蹤層級，可使用：
  - `python -m invest_research_agent list-channels --watch-tier core`
  - `python -m invest_research_agent list-channels --watch-tier normal`
- 若需要驗證 answer synthesis workflow，優先用一組已完成 analysis artifact 的真實案例做 end-to-end 測試：
  - 先建立 research artifact
  - 再用 `python -m invest_research_agent ... synthesize-answer` 產生 answer stub
  - 再用 `research-answer-synthesizer` 子 Agent 完成主要 synthesis judgment；若在 Gemini CLI 可用 `@research-answer-synthesizer` 或 `gemini -p "..."`，若在 Codex 則明確要求 spawn `research-answer-synthesizer`
- 每次 answer synthesis 驗證至少檢查：
  - JSON shape 是否符合 answer contract
  - `summary_answer` 是否直接回答問題
  - `direct_mentions` 是否真的聚焦最 relevant claims
  - `evidence` 是否保留 timestamp 或具體依據
  - `inferred_points` 是否過度延伸
  - `needs_validation` 是否對應可追蹤的後續問題
  - `citations` 是否足夠可辨識

## 5. 目前產品邊界

- 目前先把 `主題 -> 頻道 -> 最新影片 -> 筆記` 這條主流程做穩。
- 對於無字幕影片，優先考慮音訊下載與 STT provider fallback，而不是外部 grounding 流程。
- 若未來上游工具提供穩定的 `add source` 能力，再評估是否重新導入相關方案。
