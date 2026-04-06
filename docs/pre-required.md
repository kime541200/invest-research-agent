# 前置設定

這份文件只描述與 Agent 架構無關的共通前置條件。

若需要設定 MCP 客戶端，請先依目前執行環境查閱 `docs/mcp-config/` 下對應文件：

- Cursor: `docs/mcp-config/cursor.md`
- Gemini: `docs/mcp-config/gemini.md`
- Claude: `docs/mcp-config/claude.md`
- MCPorter: `docs/mcp-config/mcporter.md`

若目前環境沒有對應文件，請先搜尋現有設定檔與既有配置；若仍無法確認，再請用戶提供或補充。

## 1. 確認子模組與專案檔案

- 確認 repo 已完成 submodule 初始化。
- 確認 `modules/yt-mcp-server/` 存在。
- 確認專案根目錄存在 `resources.yaml`；若不存在，請參考 `resources.example.yaml` 協助建立。

建議指令：

```bash
git submodule update --init --recursive
```

## 2. 確認 YT MCP server 所需設定

- 確認 `modules/yt-mcp-server/.env` 存在。
- 確認 `.env` 中至少有可用的 `YOUTUBE_API_KEY`，可以參考 `modules/yt-mcp-server/docs/how-to-get-yt-api-key.md` 協助用戶取的 Youtube API Key。
- 若 `.env` 不存在，可參考 `modules/yt-mcp-server/.env.example` 建立。

## 3. 確認 YT MCP server 正常運行

先查看 `yt-mcp-server` 是否已啟動，一般情況下會運行在本機 `8088` port：

- HTTP MCP endpoint: `http://localhost:8088/mcp`

為了避免每次都重新啟動，請先確認服務是否已運行；若已運行則不需要重啟。

若需要重啟，優先使用 `modules/yt-mcp-server/` 內的啟動方式，例如：

```bash
docker compose up -d --build
```

或：

```bash
source .venv/bin/activate
python -m yt_mcp_server
```

## 4. 驗證 MCP server 可用

- 可使用 `mcp-server-tester` skill 驗證。
- 也可用 MCP `initialize` handshake 或其他健康檢查方式確認 `http://localhost:8088/mcp` 可回應。

如果 MCP server 驗證失敗，請先停止後續流程並協助排查 server 問題，確認恢復後再繼續。

## 5. 回到正式執行入口

完成以上檢查後，回到正式 CLI 入口執行主流程：

```bash
source .venv/bin/activate
python -m info_collector route-topic --topic "[使用者主題]"
python -m info_collector collect-from-topic --topic "[使用者主題]"
```
