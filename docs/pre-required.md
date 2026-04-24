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

## 5. 確認 NotebookLM MCP server 所需設定

若本次任務需要把來源匯入 NotebookLM、使用 NotebookLM research，或透過 NotebookLM 問答取得內容重點，請先確認以下條件：

- `modules/notebooklm-py/` 與 `modules/notebooklm-py/mcp/` 存在
- 已完成 NotebookLM 登入狀態配置
- 預設可用的認證檔為 `~/.notebooklm/profiles/default/storage_state.json`
- 舊版環境仍可能使用 `~/.notebooklm/storage_state.json` 作為 fallback

建議先檢查：

```bash
test -f ~/.notebooklm/profiles/default/storage_state.json && echo "profile storage_state.json exists"
```

或從 `modules/notebooklm-py/` 根目錄執行：

```bash
uv run notebooklm status
```

若尚未登入，請先由使用者執行：

```bash
uv run notebooklm login
```

## 6. 確認 NotebookLM MCP server 正常運行

先查看 `nblm-mcp-server` 是否已啟動，一般情況下會運行在本機 `8089` port：

- HTTP MCP endpoint: `http://localhost:8089/mcp`

若需要啟動，優先使用 `modules/notebooklm-py/mcp/` 內的方式，例如：

```bash
uv sync --all-packages
uv run python -m nblm_mcp_server
```

或：

```bash
docker compose up -d --build
```

## 7. 驗證 NotebookLM MCP server 可用

- 可使用 `mcp-server-tester` skill 驗證
- 也可用 `mcporter` 或 MCP `initialize` handshake 驗證 `http://localhost:8089/mcp` 是否可回應

若 NotebookLM MCP server 驗證失敗，請先停止後續 NotebookLM 相關流程並協助排查，確認恢復後再繼續。

## 8. 確認 STT provider 模式

若目前需求包含「無字幕影片也要嘗試轉字幕」，請先確認使用者希望採用哪一種 STT provider：

- 本地：以 `infra/stt/speaches/` 部署 `speaches`
- 本地 GPU：以 `infra/stt/vllm-qwen3-asr/` 部署 `vLLM + Qwen3-ASR`
- 雲端：例如 OpenAI Whisper API、Groq Whisper API

若使用者尚未決定，不要直接假設，請先詢問是要走本地還是雲端。

## 9. 確認 STT provider 設定與健康狀態

根專案 `.env` 可配置：

```env
STT_PROVIDER=speaches
STT_BASE_URL=http://localhost:8089/v1
STT_MODEL=Systran/faster-whisper-small
STT_API_KEY=
STT_TIMEOUT=300
STT_LANGUAGE=zh
STT_MAX_UPLOAD_MB=24
STT_TARGET_CHUNK_MB=8
STT_TRANSCODE_BITRATE=24k
STT_TRANSCODE_SAMPLE_RATE=16000
STT_SEGMENT_SECONDS=900
AUDIO_CACHE_POLICY=ttl
AUDIO_CACHE_TTL_DAYS=7
```

音訊快取預設會採 `ttl` 策略，並在每次執行 `collect-from-topic` 前自動清掉超過 `7` 天的舊音檔。若使用者希望轉完就刪除，可改成 `AUDIO_CACHE_POLICY=delete-on-success`。

建議先執行：

```bash
source .venv/bin/activate
python -m invest_research_agent check-stt
```

### 6.1 本地 `speaches`

- 部署入口：`infra/stt/speaches/compose.yaml`
- health endpoint：`http://localhost:8089/health`
- API base URL：`http://localhost:8089/v1`
- `python -m invest_research_agent check-stt` 會同時檢查服務是否可用，以及指定模型是否已就緒

若本地服務未啟動，可參考：

```bash
cp infra/stt/speaches/.env.example infra/stt/speaches/.env
docker compose -f infra/stt/speaches/compose.yaml --env-file infra/stt/speaches/.env up -d
```

若服務已啟動但 `check-stt` 顯示模型尚未安裝，可下載指定模型：

```bash
curl -X POST "http://localhost:8089/v1/models/Systran%2Ffaster-whisper-small"
```

### 6.2 雲端 provider

- 確認 `.env` 中至少有可用的 `STT_BASE_URL`、`STT_MODEL`、`STT_API_KEY`
- 若使用 Groq，`STT_BASE_URL` 可設為 `https://api.groq.com/openai/v1`
- 若使用 OpenAI，請使用對應 Whisper transcription endpoint 的 API base URL

### 6.3 本地 GPU `vllm-qwen3-asr`

- 部署入口：`infra/stt/vllm-qwen3-asr/compose.yaml`
- health endpoint：`http://localhost:8090/health`
- API base URL：`http://localhost:8090/v1`
- 需要可用 NVIDIA GPU 與 Docker + NVIDIA Container Toolkit

若本地 GPU 服務尚未啟動，可參考：

```bash
cp infra/stt/vllm-qwen3-asr/.env.example infra/stt/vllm-qwen3-asr/.env
docker compose -f infra/stt/vllm-qwen3-asr/compose.yaml --env-file infra/stt/vllm-qwen3-asr/.env up -d --build
```

若將服務部署在另一台 GPU 主機，只要把根專案 `.env` 的 `STT_BASE_URL` 改成對應主機的 `/v1` endpoint 即可。

若 STT provider 驗證失敗，請先停止後續流程並協助排查，確認恢復後再繼續。

## 10. 回到正式執行入口

完成以上檢查後，回到正式 CLI 入口執行主流程：

```bash
source .venv/bin/activate
python -m invest_research_agent route-topic --topic "[使用者主題]"
python -m invest_research_agent collect-from-topic --topic "[使用者主題]"
```
