# Speaches Local STT

這個目錄提供本專案預設的本機 STT 服務部署資產。

## 目的

- 以 Docker 啟動 `speaches`
- 提供本機 `http://localhost:8089/v1` 的 OpenAI-compatible STT API
- 讓 Agent 可以在前置檢查時有固定路徑可參考與排障

## 檔案

- `compose.yaml`: 本機 CPU 版部署
- `.env.example`: `compose.yaml` 會讀取的樣板設定

## 預設健康檢查

- Health URL: `http://localhost:8089/health`
- API Base URL: `http://localhost:8089/v1`
