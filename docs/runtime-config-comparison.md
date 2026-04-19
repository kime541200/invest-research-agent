# `.gemini` / `.claude` / `.codex` / `.cursor` 對照表 + 待補清單

這份文件整理目前專案在 Gemini、Claude Code、Codex、Cursor 四個執行環境中的設定現況、已對齊項目、差異點與下一步待補清單。

## 目的

- 降低三套工作流逐漸漂移的風險
- 讓後續新增 command / agent / MCP 設定時有明確對照基準
- 協助判斷哪些差異是「合理的 runtime 差異」，哪些是「仍需補齊的缺口」

---

## 一、現況總覽

| 面向 | `.gemini` | `.claude` | `.codex` | `.cursor` | 現況判斷 |
|---|---|---|---|---|---|
| MCP 設定檔 | `.gemini/settings.json` | `.claude/settings.local.json` + repo `.mcp.json` | `.codex/config.toml` | `.cursor/mcp.json` | 已可用，但格式不一致屬正常 |
| YouTube MCP server | `yt-mcp-server` | `yt-mcp-server` | 依 parent session / repo 設定決定 | `yt-mcp-server` | Codex 這層先以 subagent 對齊為主 |
| MCP URL | `http://localhost:8088/mcp` | `http://localhost:8088/mcp` | 依 parent session / repo 設定決定 | `http://localhost:8088/mcp` | 已知執行環境不同，文件需說清楚 |
| 專案 command：resources add | 有：`commands/resources/add.toml` | 有：`commands/resources/add.md` | 無 project command 結構 | 有：`commands/resources-add.md` | Codex 以主對話 + subagent 為主 |
| OpenSpec / OPSX command | 無 | 有：`commands/opsx/*` | 無 project command 結構 | 有：`commands/opsx-*` | Gemini / Codex 仍缺 command 入口 |
| transcript subagent | 有：`agents/transcript-analyst.md` | 有：`agents/transcript-analyst.md` | 有：`agents/transcript-analyst.toml` | 無明確 subagent 機制 | Gemini / Claude / Codex 已對齊 |
| research-answer-synthesizer subagent | 無明確 project 定義 | 有：`agents/research-answer-synthesizer.md` | 有：`agents/research-answer-synthesizer.toml` | 無明確 subagent 機制 | Claude / Codex 已對齊 |
| resources-add skill | 有：`skills/resources-add/SKILL.md` | 有：`skills/resources-add/SKILL.md` | 有：`skills/resources-add/SKILL.md` | 無 project skill 結構 | 核心 workflow 已抽成共享 skill |
| gh-cli skill | 有 | 有 | 無 project skill 結構 | 無 project skill 結構 | Gemini / Claude 已對齊 |
| mcp-server-tester skill | 有 | 有 | 無 project skill 結構 | 無 project skill 結構 | Gemini / Claude 已對齊 |
| mcporter skill | 有 | 有 | 無 project skill 結構 | 無 project skill 結構 | Gemini / Claude 已對齊 |
| openspec skills | 有 | 有 | 無 project skill 結構 | 無 project skill 結構 | Gemini / Claude 已對齊 |
| 專案內 MCP 文件 | 有 docs | 有 docs | 尚未補專屬 docs | 有 docs | Codex 後續可補 runtime doc |
| 官方/參考文件收納 | Gemini 參考較少 | 已加入 `references/claude-code/subagents.md` | 已加入 `references/codex/subagents/*` | 主要靠 command 範例 | 可再整理 |

---

## 二、已完成的對齊項目

### 1. YouTube channel onboarding workflow 已在 Gemini / Claude / Cursor 對齊

目前三邊都已經有「新增 YouTube 頻道到 `resources.yaml`」的 project command：

- Gemini: `.gemini/commands/resources/add.toml`
- Claude: `.claude/commands/resources/add.md`
- Cursor: `.cursor/commands/resources-add.md`

目前這組 workflow 已對齊以下核心規則：

- 先解析 channel identity
- 以 `yt-mcp-server` 作為頻道與近期影片資訊來源
- 根據近期影片推導 `tags` / `topic_keywords` / `description`
- 以目前 `resources.yaml` schema 為準
- 初始化 `channel_state.channel_id`
- 若頻道已存在，不直接覆寫
- 不碰 note / transcript / analysis artifacts

目前也已補上共享 skill：

- Gemini: `.gemini/skills/resources-add/SKILL.md`
- Claude: `.claude/skills/resources-add/SKILL.md`
- Codex: `.codex/skills/resources-add/SKILL.md`

建議後續優先維護 skill 內容，再讓 runtime-specific command 保持薄入口。

### 2. transcript-analyst subagent 已在 Gemini / Claude / Codex 對齊

- Gemini: `.gemini/agents/transcript-analyst.md`
- Claude: `.claude/agents/transcript-analyst.md`
- Codex: `.codex/agents/transcript-analyst.toml`

兩者任務目標一致：

- 讀取 transcript artifact
- 產出 analysis artifact JSON
- 不碰 routing / MCP / collection state / final note

差異主要來自 runtime frontmatter / config 格式不同，屬合理差異：

- Gemini 使用 `kind`, `temperature`, `max_turns`
- Claude 使用 `tools`, `maxTurns`, `color`
- Codex 使用 `name`, `description`, `developer_instructions`

### 3. research-answer-synthesizer subagent 已在 Claude / Codex 對齊

- Claude: `.claude/agents/research-answer-synthesizer.md`
- Codex: `.codex/agents/research-answer-synthesizer.toml`

兩者任務目標一致：

- 讀取 research artifact 與使用者問題
- 產出 research answer JSON
- 負責 relevant claim selection 與 answer-boundary judgment
- 不碰 routing / collection state / final note

### 4. Claude 已補齊原本 Gemini 有的多數 project skills

目前 `.claude/skills/` 已包含：

- `gh-cli`
- `mcp-server-tester`
- `mcporter`
- `openspec-apply-change`
- `openspec-archive-change`
- `openspec-explore`
- `openspec-propose`

這讓 Claude 在 repo 內的專案操作能力，已不再明顯落後 Gemini。

### 5. Claude / Cursor 已補齊 OPSX command 入口

- Claude: `.claude/commands/opsx/{propose,explore,apply,archive}.md`
- Cursor: `.cursor/commands/opsx-{propose,explore,apply,archive}.md`

這表示 Claude / Cursor 已經可以直接承接 OpenSpec / OPSX 工作流。

---

## 三、四方差異拆解

## A. MCP 設定層

### Gemini

檔案：`.gemini/settings.json`

特點：

- 有 `context.fileName` 指向 `./AGENTS.md`
- 明確宣告 `mcpServers`
- 有 `mcp.allowed`
- 有 `skills.enable`

優點：

- 專案上下文與 MCP 允許名單集中在同一檔
- 設定完整度高

缺點：

- 結構較 Gemini-specific，難直接拿去給其他 runtime 共用

### Claude

檔案：

- `.claude/settings.local.json`
- repo root `.mcp.json`

特點：

- `.claude/settings.local.json` 只負責啟用 project MCP
- `.mcp.json` 負責宣告 server 內容

優點：

- 符合 Claude Code 慣用拆法
- 專案 MCP 可集中在 repo root

缺點：

- 設定散在兩個地方，新加入成員較不容易一眼看懂
- 目前沒有像 Gemini 那樣明確掛 project context 檔案

### Cursor

檔案：`.cursor/mcp.json`

特點：

- 結構最單純
- 只放 MCP server 宣告

優點：

- 維護成本低

缺點：

- 只解決 MCP，不涵蓋 skills / agents / richer project workflow

### 判斷

這一層「不需要強行做成同格式」，因為三個 runtime 的設定入口本來就不同。
真正應維持一致的是：

- server name = `yt-mcp-server`
- url = `http://localhost:8088/mcp`
- 文件說明一致

---

## B. Command 層

### 已對齊

| 能力 | Gemini | Claude | Cursor |
|---|---|---|---|
| resources add | 有 | 有 | 有 |

### 未完全對齊

| 能力 | Gemini | Claude | Cursor | 判斷 |
|---|---|---|---|---|
| opsx-propose | 無 command | 有 | 有 | Gemini 缺 command 入口 |
| opsx-explore | 無 command | 有 | 有 | Gemini 缺 command 入口 |
| opsx-apply | 無 command | 有 | 有 | Gemini 缺 command 入口 |
| opsx-archive | 無 command | 有 | 有 | Gemini 缺 command 入口 |

### 判斷

Gemini 目前有 openspec skills，但缺少 project command 入口。
這代表：

- Claude / Cursor：可直接用 command 啟動 workflow
- Gemini：偏向需要手動叫 skill 或走其他方式

這是目前最明顯的體驗落差之一。

---

## C. Agent / Subagent 層

| 能力 | Gemini | Claude | Cursor |
|---|---|---|---|
| transcript-analyst | 有 | 有 | 不適用 / 無同等結構 |

### 判斷

- Gemini、Claude、Codex 都已有 project-level transcript analysis subagent
- Cursor 目前主要是 command 導向，沒有同樣的 repo-level subagent 結構可直接對位

因此這一層不建議硬做四個 runtime 完全一致，而是：

- Gemini / Claude / Codex 維持 agent parity
- Cursor 只補足實際常用 workflow command 即可

---

## D. Skill 層

### Gemini / Claude 已基本對齊

兩邊目前都有：

- `gh-cli`
- `mcp-server-tester`
- `mcporter`
- `openspec-*`

### Cursor

Cursor 在這個 repo 內目前沒有相同的 skill 目錄結構，因此不適合直接比「skill 數量」。
比較合理的對齊單位應該是：

- 使用者是否能完成同一件事
- 若能，靠的是 command 還是其他 runtime 機制

---

## E. 文件 / Reference 層

### 目前狀況

- Gemini 有：`docs/mcp-config/gemini.md`
- Claude 有：`docs/mcp-config/claude.md`
- Cursor 有：`docs/mcp-config/cursor.md`
- Claude 另外已有：`references/claude-code/subagents.md`
- Gemini 也有對應參考：`references/gemini-cli/custom-commands.md`、`references/gemini-cli/subagents.md`
- Codex 也有對應參考：`references/codex/subagents/concept.md`、`references/codex/subagents/setup.md`

### 判斷

文件面已經有基本對應，但仍有兩個小缺口：

1. 缺少一份「專案 runtime strategy」總覽文件
   - 目前資訊散在 docs / references / runtime config 之間
   - 新加入的人不容易一眼看懂 repo 是「多 runtime 並存」策略

2. 缺少一份「新增功能時要同步哪些 runtime」的維護規則
   - 目前要靠人工記憶
   - 容易出現只改 `.claude/` 沒補 `.gemini/` 或 `.cursor/` 的情況

---

## 四、建議的待補清單

以下按優先級排列。

### P1：補齊 Gemini 的 OPSX command 入口

**建議新增：**

- `.gemini/commands/opsx/propose.toml`
- `.gemini/commands/opsx/explore.toml`
- `.gemini/commands/opsx/apply.toml`
- `.gemini/commands/opsx/archive.toml`

**原因：**

- Gemini 雖然已有 openspec skills，但缺 command 入口
- 目前 Claude / Cursor 已有對應 command，Gemini 形成工作流落差
- 補上後三邊的「變更提案 / 探索 / 套用 / 封存」操作會更一致

**建議做法：**

- 不要盲目複製 `.claude/commands/opsx/*.md`
- 以 Gemini command 格式重寫，但保持相同任務意圖與 guardrails

---

### P1：建立 runtime 維護規則文件

**建議新增：**

- 例如 `docs/runtime-maintenance.md`

**內容建議：**

- 哪些能力應跨 runtime 同步：`resources add`、OPSX commands、MCP server 名稱與 URL
- 哪些能力只需 Gemini / Claude / Codex 對齊：subagents
- 哪些能力只需 Gemini / Claude 對齊：skills
- 哪些差異屬 runtime-specific，可保留不同格式：settings frontmatter、MCP config shape
- 新增 command / agent / skill 時的同步檢查清單

**原因：**

- 現在 repo 已經明顯是多 runtime 維護模式
- 沒有維護規則時，後續很容易再次漂移

---

### P2：整理 `.claude` 與 `.gemini` 的 skill 來源策略

**目前觀察：**

- `.gemini/skills/*` 與 `.claude/skills/*` 有大量相似內容
- 未來若兩邊持續各自複製，維護成本會越來越高

**可考慮方向：**

- 明確標記哪些 skill 是「共享來源」
- 或建立一份簡單規則：哪些 skill 要雙邊同步、哪些只屬某一 runtime

**原因：**

- 這不是立即阻塞問題，但長期最容易造成內容漂移

---

### P2：補一份 runtime capability matrix 到 README 或 docs 首頁

**建議內容：**

- 使用 Gemini / Claude / Codex / Cursor 時，各自支援哪些操作
- MCP / commands / agents / skills 各在哪裡設定

**原因：**

- 現在 README 有提到三份 MCP 文件，但沒有整體對照圖
- 對新使用者不夠直觀

---

### P3：評估是否統一 Cursor command 命名風格

**目前狀況：**

- Cursor 使用扁平命名：`opsx-propose.md`、`resources-add.md`
- Claude 使用巢狀目錄：`opsx/propose.md`、`resources/add.md`

**判斷：**

- 這比較像 runtime-specific 命名差異，不一定要改
- 只要文件有說清楚即可

因此這項優先度較低，除非後續 Cursor 端出現更多 command 導致查找困難。

---

## 五、建議的同步原則

後續若再新增功能，建議用下面原則判斷是否要同步：

### 應優先跨 runtime 同步的項目

- 與專案主工作流直接相關的 command
- MCP server 名稱 / URL / 啟用方式文件
- 會影響使用者是否能完成核心任務的入口能力

### 應優先 Gemini / Claude 同步的項目

- subagents
- skills
- 需要較強 agent orchestration 的能力

### 可以接受 runtime-specific 差異的項目

- settings 檔名與 JSON 形狀
- command frontmatter 格式
- agent frontmatter 細節
- Cursor 是否沒有對等 subagent 結構

---

## 六、目前結論

目前四個 runtime 的狀態可以總結成一句話：

> 核心的 MCP 與 `resources add` workflow 已基本對齊；Claude 已大幅補上原本相對缺少的 project 能力；下一步最值得做的是補齊 Gemini 的 OPSX command 入口，並建立一份明確的多 runtime 維護規則。

---

## 七、建議下一步

如果要繼續做，建議順序如下：

1. 補 `.gemini/commands/opsx/*`
2. 新增 `docs/runtime-maintenance.md`
3. 視需要把這份對照表摘要連到 README 或 docs 首頁
