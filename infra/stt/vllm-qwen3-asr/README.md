# vLLM Qwen3-ASR

這個目錄提供本專案的 GPU 型本地 STT 部署資產，使用 `vLLM` 啟動 `Qwen/Qwen3-ASR-1.7B`，並透過 OpenAI-compatible API 對外提供音訊轉寫服務。

## 目的

- 以 Docker Compose 啟動 `vLLM`
- 對外提供 `http://localhost:8090/v1`
- 讓根專案沿用既有 `SttClient` 呼叫 `/v1/audio/transcriptions`

## 先決條件

- Linux 主機或其他可用 NVIDIA GPU 的環境
- Docker Engine 與 Docker Compose plugin
- NVIDIA Container Toolkit
- 可下載 Hugging Face 模型的網路環境

## 檔案

- `Dockerfile`: 以 `vllm/vllm-openai` 為基底，補上 `vllm[audio]`
- `compose.yaml`: GPU 版服務定義
- `.env.example`: compose 用設定樣板

## 快速開始

```bash
cp infra/stt/vllm-qwen3-asr/.env.example infra/stt/vllm-qwen3-asr/.env
docker compose -f infra/stt/vllm-qwen3-asr/compose.yaml --env-file infra/stt/vllm-qwen3-asr/.env up -d --build
```

## 預設端點

- Health URL: `http://localhost:8090/health`
- API Base URL: `http://localhost:8090/v1`

## 根專案 `.env` 參考設定

```env
STT_PROVIDER=vllm-qwen3-asr
STT_BASE_URL=http://localhost:8090/v1
STT_MODEL=Qwen/Qwen3-ASR-1.7B
STT_API_KEY=EMPTY
STT_TIMEOUT=300
STT_LANGUAGE=zh
STT_MAX_UPLOAD_MB=24
STT_TARGET_CHUNK_MB=8
STT_TRANSCODE_BITRATE=24k
STT_TRANSCODE_SAMPLE_RATE=16000
STT_SEGMENT_SECONDS=900
```

## 備註

- 官方 Docker image 預設不含 audio optional dependencies，所以這裡用自訂 `Dockerfile` 額外安裝 `vllm[audio]`。
- 若未來 `Qwen3-ASR` 需要更新的 `transformers`，可在 `.env` 裡調整 `HF_TRANSFORMERS_SPEC`，例如改成 `git+https://github.com/huggingface/transformers.git`。
- 即使是 GPU provider，也建議保留目前專案中的音訊轉碼與切塊前處理，避免長音檔拖慢整體轉寫流程。
