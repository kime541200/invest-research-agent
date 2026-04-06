# Cursor MCP 設定

這份文件說明如何在 Cursor 中啟用 `yt-mcp-server`。

## 設定檔位置

專案目前使用的 Cursor MCP 設定檔為：

- `.cursor/mcp.json`

## 最小設定

```json
{
  "mcpServers": {
    "yt-mcp-server": {
      "url": "http://localhost:8088/mcp"
    }
  }
}
```

## 檢查重點

- `yt-mcp-server` 名稱與 repo 內其他文件一致
- URL 指向 `http://localhost:8088/mcp`
- `yt-mcp-server` 已先在本機正常啟動

## 若設定檔不存在

- 先確認目前是否真的在使用 Cursor
- 若是 Cursor 專案但沒有 `.cursor/mcp.json`，請協助建立
- 建立後通常需要重新整理工作區或重新開啟對話，讓 MCP 設定重新載入

## 若格式不一致

Cursor 的 MCP 設定格式可能會隨版本或 Agent 整合方式不同而調整。

處理順序建議如下：

1. 先讀 repo 內現有 `.cursor/mcp.json`
2. 若專案沒有該檔，搜尋目前 Cursor 使用中的 MCP 設定位置
3. 若仍無法確認，再請用戶提供目前使用的 Cursor MCP 設定格式
