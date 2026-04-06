## Context

目前 `info-collector` 的主流程會先透過 `yt-mcp-server` 取得 YouTube 原生字幕，再將字幕內容整理成 Markdown 筆記。當影片回傳 `transcripts_disabled` 或其他字幕不可用狀態時，系統只能退回影片描述，導致筆記品質與可分析性明顯下降。

這次變更需要補上一條與現有字幕流程相容的 fallback 路徑，同時兼顧兩個約束：

- 使用者應以自然語言驅動 Agent，不需要理解 Docker、STT provider 或 API 細節。
- STT 服務必須可以在本地與雲端之間切換，因此專案內部應以 provider 抽象與標準 HTTP 介面整合，而不是綁定單一實作。

本地部署將先以 `infra/stt/speaches` 作為標準方案，並保留未來切換到 OpenAI、Groq 等雲端 STT 服務的空間。

## Goals / Non-Goals

**Goals:**
- 在原生字幕不可用時，提供「下載音訊 -> STT -> TranscriptBundle」的 fallback 流程。
- 讓 `info-collector` 只依賴一組 STT provider 設定（`provider`、`base_url`、`model`、`api_key` 等），不直接依賴特定本地服務。
- 在 repo 內提供 `speaches` 的本機部署資產，作為可重複使用的標準本地方案。
- 將前置檢查流程擴充為可檢查 STT provider 是否健康，並由 Agent 協助排障與啟動。

**Non-Goals:**
- 第一階段不追求即時串流轉錄、TTS 或語音聊天能力。
- 第一階段不處理所有雲端 provider 的正式接入，只先定義抽象與設定模型。
- 第一階段不重寫既有 note generator，而是將 STT 結果正規化為既有 `TranscriptBundle` 後重用現有流程。
- 第一階段不把 STT 服務做成 MCP server；先以 HTTP API 為主。

## Decisions

### 1. 以 `yt-dlp` 作為音訊下載層

系統將在字幕 fallback 路徑中直接使用 `yt-dlp` 的 Python library 下載音訊，而不是依賴外部 Agent skill 或互動式下載流程。

理由：
- `yt-dlp` 已經是成熟的 YouTube 媒體下載能力，適合納入可重跑 pipeline。
- 使用 Python library 比依賴 shell script 或 editor skill 更容易測試、快取與控制錯誤。
- `yt-dlp` 將作為專案正式依賴加入 `pyproject.toml`，並安裝在專案 `.venv` 中，而不是要求全域安裝。

替代方案：
- 沿用外部 skill：不適合正式 pipeline，互動性太強。
- 下載完整影片再抽音訊：比直接抓音訊多耗時與空間。

### 1.1 第一階段避免要求 host 全域安裝 `ffmpeg`

第一階段將優先採用「下載原始音訊流後直接送 STT 容器」的策略，盡量避免在 host 端做音訊轉檔、抽取或後處理，因此不把全域 `ffmpeg` 視為必要前置條件。

理由：
- `ffmpeg` 是外部 binary，不適合像 Python 套件一樣由 `pyproject.toml` 管理。
- 若 host 端不做轉檔，而是由 STT 容器處理解碼與轉錄，使用者就不需要理解或手動安裝本機多媒體工具鏈。
- 這符合本專案希望由 Agent 協助跑通環境、而不是要求使用者先熟悉 Docker 或系統層工具的方向。

替代方案：
- 要求使用者全域安裝 `ffmpeg`：設定簡單，但與專案隔離與自然語言操作目標衝突。
- 在 repo 中攜帶平台相關 `ffmpeg` binary：可避免全域安裝，但會增加跨平台維護成本。
- 在第一階段就把所有音訊正規化與切片都放到 host 端處理：彈性較高，但會提早引入額外依賴與複雜度。

### 2. 以 STT provider 抽象整合本地與雲端服務

系統內部將引入 STT provider 設定模型，最少包含：
- `provider`
- `base_url`
- `model`
- `api_key`
- `timeout`
- `language`

理由：
- 使用相同抽象即可在本地 `speaches`、OpenAI、Groq 間切換。
- 主流程只需要知道「送音檔到 STT 服務」而非背後部署方式。

替代方案：
- 將 `speaches` 細節硬編碼進主程式：短期快，但未來替換成本高。
- 先只做本地 provider：會讓後續擴充雲端 provider 時需要再重構一次。

### 3. 本地預設 provider 為 `speaches`，並在 repo 中提供 `infra/stt/speaches`

本地標準部署方案將落在 `infra/stt/speaches`，包含 compose 與相關設定樣板。

理由：
- 使用者與 Agent 可以在 repo 中找到單一明確的部署入口。
- 有助於 pre-required 文件與自動檢查流程標準化。

替代方案：
- 直接引用 upstream compose：更新方便，但專案難以加入自訂 healthcheck 與環境預設。
- 將部署檔放專案根目錄：擴充不同 provider 時會變雜。

### 4. STT 回應一律正規化成既有 `TranscriptBundle`

不論來自本地或雲端 provider，最終都要轉成與現有字幕流程一致的 `TranscriptBundle`，包含全文、segments、merged segments 等欄位。

理由：
- 讓 `note_generator`、orchestrator 等既有邏輯可最大程度重用。
- 降低「字幕來源不同」造成的下游分支邏輯。

替代方案：
- 讓 note generator 直接理解多種 STT 回應格式：會擴散複雜度。

### 5. pre-required 流程新增 STT provider 健康檢查與互動決策

前置檢查將新增 STT provider 檢查：
- 本地模式：檢查 Docker/compose 與 `/health`
- 雲端模式：檢查 `base_url`、`model`、`api_key` 與最小健康探測

若缺少關鍵資訊，Agent 應先問使用者要走本地或雲端。

理由：
- 這符合「自然語言驅動」的產品方向，讓使用者不必先手動準備底層服務。

## Risks / Trade-offs

- [本地 CPU STT 速度較慢] → 先限制為字幕 fallback 路徑，並透過音檔與轉錄快取降低重跑成本。
- [不同 provider 的 response 格式不一致] → 將所有 provider 回應先經過統一 adapter 再轉為 `TranscriptBundle`。
- [`yt-dlp` 對 YouTube 規則變化敏感] → 將音訊下載層獨立封裝，並在失敗時保留清楚的錯誤狀態與重試空間。
- [部分下載或後處理情境最終仍可能需要 `ffmpeg`] → 第一階段先避免 host 端轉檔；若後續需要切片或格式正規化，再優先評估容器內處理而非要求全域安裝。
- [本地 `speaches` 初次下載模型較慢] → 在部署資產中提供 model preload 與 cache volume。
- [雲端 provider 需要額外金鑰與費用] → 由前置檢查與設定文件明確引導，避免在 fallback 階段才暴露缺設定問題。

## Migration Plan

1. 新增 `infra/stt/speaches` 目錄與本地部署資產。
2. 新增 STT provider 設定模型與讀取方式。
3. 新增音訊下載與 STT client/provider adapter。
4. 在 orchestrator 中加入字幕 fallback 決策。
5. 擴充 `docs/pre-required.md` 與 README，納入 STT provider 檢查與部署說明。
6. 以本地 `speaches` 完成 smoke test，確認能把音檔轉成可用字幕。

若 rollout 失敗，可先關閉 fallback 路徑，退回目前僅使用原生字幕的流程。

## Open Questions

- fallback 的觸發條件是否只限 `transcripts_disabled`，還是也包含 `no_transcript_found`？
- 第一版是否需要把 STT 輸出的 `.srt` / `.vtt` 落地保存，作為除錯與快取資產？
- 對於長影片，是否需要在下載後先做音訊切片再送 STT，以控制 timeout 與資源消耗？
