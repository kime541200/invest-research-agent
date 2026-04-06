## Why

目前主流程高度依賴 YouTube 原生字幕；一旦影片沒有字幕或字幕被停用，就只能退回影片描述，無法穩定產出可分析的筆記內容。現在需要補上一條可重跑、可替換 provider 的 STT fallback 路徑，讓無字幕影片也能回到既有字幕導向的筆記流程。

## What Changes

- 新增以音檔轉字幕為核心的 fallback 流程：當原生字幕不可用時，先下載影片音訊，再透過 STT 服務取得逐字稿。
- 新增 STT provider 抽象與設定模型，支援本地 `speaches` 與未來雲端 provider（例如 OpenAI、Groq）共用同一組 `base_url`、`model`、`api_key` 設定介面。
- 在 repo 中新增 `infra/stt/speaches` 部署資產，作為本機 Docker STT 服務的標準落地方案。
- 擴充前置檢查流程與後續文件，讓 Agent 能協助檢查 STT 服務是否可用，並依本地或雲端模式協助完成設定。

## Capabilities

### New Capabilities
- `audio-transcription-fallback`: 在 YouTube 原生字幕不可用時，自動下載音訊並以 STT 取得可供後續分析的逐字稿。
- `stt-provider-management`: 管理本地與雲端 STT provider 的設定、健康檢查與部署入口。

### Modified Capabilities

None.

## Impact

- Affected code: `src/info_collector/` 的 orchestrator、下載音訊與 STT client/provider 抽象
- Affected infra: 新增 `infra/stt/speaches/` 的 Docker 部署資產
- Affected config: 根專案 `.env` / `.env.example` 需新增 STT 相關設定
- Affected docs: `docs/pre-required.md`、`README.md` 與 Agent 規則需納入 STT provider 檢查與設定流程
- Dependencies: `yt-dlp` 下載音訊能力，以及本地 `speaches` 或雲端 STT API
