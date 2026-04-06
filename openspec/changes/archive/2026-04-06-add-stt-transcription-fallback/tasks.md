## 1. STT 基礎設施與設定

- [x] 1.1 建立 `infra/stt/speaches/` 目錄，加入本機 Docker 部署所需的 compose 與設定樣板
- [x] 1.2 定義根專案 STT 設定欄位與載入方式，涵蓋 `provider`、`base_url`、`model`、`api_key`、`timeout`、`language`
- [x] 1.3 實作 STT provider 健康檢查邏輯，至少支援本地 `speaches` 與預留雲端 provider 設定驗證

## 2. 音訊下載與轉錄整合

- [x] 2.1 在 Python 專案中加入 `yt-dlp` 依賴，實作非互動式音訊下載模組
- [x] 2.2 實作 STT HTTP client 與 provider adapter，將 STT 回應正規化為既有 `TranscriptBundle`
- [x] 2.3 在 orchestrator 或對應流程中加入「原生字幕失敗 -> 音訊下載 -> STT fallback」決策
- [x] 2.4 為音訊下載、STT 成功與失敗路徑補上測試，覆蓋可重跑與 graceful degradation 行為

## 3. 文件與 Agent 操作流程

- [x] 3.1 更新 `docs/pre-required.md`，加入 STT provider 的檢查、互動決策與排障流程
- [x] 3.2 更新 `README.md`，補充本地 `speaches` 部署方式與未來雲端 provider 設定方向
- [x] 3.3 補充 Agent 規則或相關指引，說明前置檢查時如何先確認使用本地或雲端 STT
- [x] 3.4 以本地 `speaches` 完成一次 smoke test，驗證音檔可成功轉成字幕並回到既有筆記流程
