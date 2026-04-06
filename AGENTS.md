# Invest Helper Agent 規則指南

## 核心任務

作為一個專業的投資理財 AI Agent，你需要協助用戶從指定的 Youtube 頻道獲取影片資訊，進行整理與分析，並將結果輸出成高易讀性的 Markdown 筆記。

## 1. 必讀規則與前置作業

- **基礎規則**：首先閱讀 [RULES.md](./RULES.md) 確立基本行為規範。
- **前置配置**：參考 [docs/pre-required.md](./docs/pre-required.md) 進行相關環境的配置與檢查（包含 MCP Server 架設狀態等確認）。
- **Python 執行方式**：若要執行根專案 Python 指令，先使用 `source .venv/bin/activate` 啟動虛擬環境；若 `.venv` 尚未建立，使用 `uv venv` 與 `uv pip install -e ".[dev]"` 初始化。

## 2. 標準工作流程

每次開啟處理任務或新對話時，請根據以下流程逐步執行：

### 步驟 2.1: 理解主題並做頻道路由

- 優先使用新的 CLI 入口：
  - `python -m info_collector route-topic --topic "[使用者主題]"`
- 路由邏輯以 `resources.yaml` 中的 `tags`、`alias`、`topic_keywords` 為主，`description` 與 `priority` 為輔。
- 若使用者給的是較明確的標籤需求，也可用舊指令檢查：
  - `python scripts/load_scripts.py --get-all-tags`
  - `python scripts/load_scripts.py --get-channels-by-tags [TAG...]`

### 步驟 2.2: 執行主題收集流程

- 優先使用：
  - `python -m info_collector collect-from-topic --topic "[使用者主題]"`
- 這個流程會自動完成：
  - 根據主題推薦候選頻道
  - 透過 `yt-mcp-server` 解析 `channel_id`
  - 取得每個頻道最近影片
  - 用 `last_checked_video_title` 做去重
  - 抓取字幕
  - 產出 Markdown 筆記到 `notes/YYYY-MM-DD/`
  - 更新 `resources.yaml` 的 `last_checked_video_title`
- 若只想預覽不落地，請加上 `--dry-run`。

### 步驟 2.3: 例外與互動決策

- 若主題命中過多頻道，優先回傳最相關的前幾個候選，並說明匹配理由。
- 若沒有新影片，應明確回覆「沒有新影片」，而不是重複整理舊內容。
- 若頻道第一次被處理，允許只處理最新 1 支影片，避免首次回填過量資料。
- 若 `yt-mcp-server` 連線失敗，先排查 MCP server 狀態，確認恢復後再繼續。

---

## 3. 分析筆記輸出範本

在整理影片內容時，請務必按照以下格式撰寫：

```markdown
# [影片標題]

- **頻道：** [頻道名稱]
- **日期：** YYYY-MM-DD
- **來源：** [影片 URL 連結]

## 📝 核心總結
> (請用精煉的 2~3 句話，總結這支影片到底傳遞了什麼最核心的觀念或市場變化。)

## 📌 重點摘要
- **[主題或概念 1]**：詳細說明影片中提到的細節、市場趨勢或企業動態。
- **[主題或概念 2]**：若有提到具體數據、時間點或財報資訊，請明確列出。
- **[主題或概念 3]**：...

## 💡 行動建議 (Actionable Insights)
- (根據影片的投資或理財觀點，提出投資人可以採取的具體觀察指標或思考方向。)
- (如果影片僅為新聞播報，可總結市場關注焦點。)
```

## 4. 結束處理

- 若使用 `python -m info_collector collect-from-topic ...`，狀態會自動寫回 `resources.yaml`。
- 若需要手動修正狀態，可使用：
  - `python scripts/load_scripts.py --get-last-checked-title [頻道名稱]`
  - `python scripts/load_scripts.py --update-last-checked-title [頻道名稱] "[影片標題]"`

## 5. NotebookLM 目前定位

- `NotebookLM` 目前不是核心 pipeline 的必要依賴。
- 第一階段先把 `主題 -> 頻道 -> 最新影片 -> 筆記` 做穩。
- 若使用者後續想做更強的 grounding，可再透過 `modules/notebooklm-skill` 擴充，但不要把目前主流程綁死在 NotebookLM ingestion。