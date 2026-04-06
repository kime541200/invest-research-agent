# Gemini MCP 設定

這份文件說明如何在 Gemini 環境中啟用 `yt-mcp-server`。

## 設定檔位置

專案目前使用的 Gemini 設定檔為：

- `.gemini/settings.json`

## 最小設定

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

## 專案目前可參考的完整範例

```json
{
  "context": {
    "fileName": ["./AGENTS.md"]
  },
  "mcpServers": {
    "yt-mcp-server": {
      "url": "http://localhost:8088/mcp"
    }
  },
  "mcp": {
    "allowed": ["yt-mcp-server"],
    "excluded": []
  },
  "skills": {
    "enable": ["mcp-server-tester"],
    "disable": []
  }
}
```

## 檢查重點

- `yt-mcp-server` 名稱與 repo 內其他文件一致
- URL 指向 `http://localhost:8088/mcp`
- `mcp.allowed` 已允許 `yt-mcp-server`
- `yt-mcp-server` 已先在本機正常啟動

## 若設定檔不存在

- 先確認目前是否真的在使用 Gemini 環境
- 若是 Gemini 專案但沒有 `.gemini/settings.json`，請協助建立
- 建立後通常需要重新開啟對話，讓設定重新載入

## 若格式不一致

Gemini 的設定格式可能會因 Agent 整合方式不同而調整。

處理順序建議如下：

1. 先讀 repo 內現有 `.gemini/settings.json`
2. 若專案沒有該檔，搜尋目前 Gemini 使用中的設定位置
3. 若仍無法確認，再請用戶提供目前使用的 Gemini 設定格式
