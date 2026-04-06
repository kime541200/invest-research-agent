# 前置設定

## 1. 啟動 YT MCP server

先查看 Youtube MCP server 是否已啟動，一般情況下會運行在本機的 8088 port。
如果沒有啟動，請先把 `https://github.com/kime541200/yt-mcp-server.git` clone 下來，並根據該專案的指示進行配置，若有需要設定 Youtube API Key，請先協助用戶進行配置及設定（相關操作說明都放在 `yt-mcp-server` repo 中）。

## 2. 確認 MCP server 正確運行

請參考 mcp-server-tester 這個 Agent Skill 確認 MCP server 正常運行。

> 為了避免每次都重新啟動 MCP server，請先確認 MCP server 是否已啟動，若已啟動則不需要再啟動。
>
> 因為該 MCP server 中使用的函式庫可能會因為更新導致無法正常運行，若 mcp-server-tester 執行失敗，請先停止動作並協助用戶看看該 MCP server 是哪邊發生問題，只有在 MCP server 正常運行的情況下才能繼續往下執行。

## 3. 檢查 MCP server 連線配置

請檢查 [settings.json](.gemini/settings.json) 中的配置，確保 MCP server 有正確啟用：

```json
{
  "mcpServers": {
    "yt-mcp-server": {
      "url": "http://localhost:8088/mcp"
    }
  },
  "mcp": {
    "allowed": ["yt-mcp-server"],
    "excluded": []
  }
}
```

如果沒有正確配置，請先進行該配置，並要求用戶重新啟動對話。

## 4. 檢查來源資料清單

檢查當前目錄是否存在 `resources.yaml`，如果沒有，請參考 `resources.example.yaml` 並協助用戶建立一個新的 `resources.yaml`。
