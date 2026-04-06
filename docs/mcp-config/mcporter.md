# MCPorter 存取 MCP

這份文件說明如何透過 `mcporter` 直接訪問 `yt-mcp-server`。

`mcporter` 是一個可直接呼叫 MCP server 的 CLI / TypeScript runtime，支援：

- 自動發現已配置的 MCP servers
- 直接對 HTTP 或 stdio MCP endpoint 做 ad-hoc 呼叫
- 將設定寫入專案層 `config/mcporter.json`

相關能力可參考 [mcporter repo](https://github.com/steipete/mcporter)。

## 本專案使用方式

本專案已提供：

- `config/mcporter.json`

因此在專案根目錄通常可以直接使用：

```bash
npx mcporter list
npx mcporter list yt-mcp-server --schema
```

## 常用指令

列出目前可用的 MCP servers：

```bash
npx mcporter list
```

查看 `yt-mcp-server` 的 tools 與 schema：

```bash
npx mcporter list yt-mcp-server --schema
```

直接呼叫工具：

```bash
npx mcporter call yt-mcp-server.channels_searchChannels query=@inside6202 max_results=3
npx mcporter call yt-mcp-server.channels_listVideos channel_id=UCVlH0xJHnJxw0Wj8iYl9f6Q max_results=3
npx mcporter call yt-mcp-server.transcripts_getTranscript video_id=7U1qyLstvBU
```

若要輸出機器可讀結果，可加上：

```bash
npx mcporter list yt-mcp-server --schema --json
npx mcporter call yt-mcp-server.transcripts_getTranscript video_id=7U1qyLstvBU --output json
```

## 不透過設定檔的 ad-hoc 用法

若不想先寫設定，也可以直接指向 HTTP endpoint：

```bash
npx mcporter list http://localhost:8088/mcp --all-parameters
npx mcporter call http://localhost:8088/mcp.transcripts_getTranscript video_id=7U1qyLstvBU
```

## 設定檔位置

`mcporter` 預設會先讀專案內：

- `config/mcporter.json`

若需要，也可另外搭配：

- `~/.mcporter/mcporter.json`

## 檢查重點

- `yt-mcp-server` 已先在本機正常啟動
- `config/mcporter.json` 內的 URL 指向 `http://localhost:8088/mcp`
- 若有多個環境設定來源，請確認 `mcporter list` 看到的 `yt-mcp-server` 定義是否正確

## 何時優先用 mcporter

以下情況特別適合優先使用 `mcporter`：

- 想快速驗證 MCP server 是否可用
- 想直接從 shell 呼叫工具，不依賴特定 Agent UI
- 想用一致方式訪問不同 MCP servers
- 想避免先處理 Cursor / Gemini / Claude 的設定差異
