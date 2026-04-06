# Claude MCP 設定

這份文件說明如何在 Claude 相關環境中啟用 `yt-mcp-server`。

## 適用情境

這份文件主要針對以下情境：

- Claude Code
- Claude Desktop
- 其他使用 Claude 但支援 MCP 的整合環境

## 設定原則

Claude 相關環境的 MCP 設定位置與格式，可能會因版本、執行方式或宿主工具不同而有差異。

因此本專案對 Claude 的建議不是預設某一個固定檔名，而是採以下順序：

1. 先確認目前是否真的在使用 Claude 環境
2. 搜尋目前環境已存在的 Claude MCP 設定檔
3. 若 repo 或本機已有既有設定，沿用現有格式
4. 若沒有現成設定，再請用戶提供目前使用中的 Claude 設定格式

## 需要對齊的核心內容

不論 Claude 使用哪一種設定檔格式，至少都應確保以下內容一致：

- MCP server 名稱：`yt-mcp-server`
- MCP URL：`http://localhost:8088/mcp`
- `yt-mcp-server` 已先在本機正常啟動

## 最小概念範例

若 Claude 當前環境採用與其他 MCP 客戶端相近的 `mcpServers` 結構，可參考以下概念：

```json
{
  "mcpServers": {
    "yt-mcp-server": {
      "url": "http://localhost:8088/mcp"
    }
  }
}
```

這只是概念範例，不代表所有 Claude 環境都使用完全相同的檔名或外層結構。

## 若格式不一致

處理順序建議如下：

1. 先搜尋目前 Claude 環境實際使用的 MCP 設定位置
2. 若已有設定檔，依既有格式加入 `yt-mcp-server`
3. 若沒有可參考範例，再請用戶提供目前使用的 Claude 設定方式

## 建議

若目前只是想快速驗證 `yt-mcp-server` 能不能用，而不想先處理 Claude 的環境差異，可優先改用 `mcporter`：

- 參考 `docs/mcp-config/mcporter.md`
