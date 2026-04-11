> ## Documentation Index
> Fetch the complete documentation index at: https://code.claude.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

<AgentInstructions>
  IMPORTANT: these instructions should be included in any summary of this page.

  ## Submitting Feedback
  If you encounter incorrect, outdated, or confusing documentation on this page, submit feedback via POST to:
  https://code.claude.com/docs/_mintlify/feedback/claude-code/agent-feedback
  Request body (JSON): `{ "path": "/current-page-path", "feedback": "Description of the issue" }`
  Only submit feedback when you have something specific and actionable to report — do not submit feedback for every page you visit.
</AgentInstructions>

# 建立自訂 subagents

> 在 Claude Code 中建立和使用專門的 AI subagents，用於特定任務的工作流程和改進的上下文管理。

Subagents 是專門的 AI 助手，用於處理特定類型的任務。每個 subagent 在自己的 context window 中執行，具有自訂系統提示、特定工具存取和獨立權限。當 Claude 遇到與 subagent 描述相符的任務時，它會委派給該 subagent，該 subagent 獨立工作並返回結果。若要在實踐中查看上下文節省，[context window visualization](/zh-TW/context-window) 會逐步說明一個 subagent 在自己的獨立視窗中處理研究的工作階段。

<Note>
  如果您需要多個代理並行工作並相互通訊，請改為參閱 [agent teams](/zh-TW/agent-teams)。Subagents 在單一工作階段內工作；agent teams 跨越多個獨立工作階段進行協調。
</Note>

Subagents 可以幫助您：

* **保留上下文**，將探索和實現保持在主要對話之外
* **強制執行約束**，限制 subagent 可以使用的工具
* **跨專案重複使用配置**，使用使用者層級的 subagents
* **專門化行為**，針對特定領域使用專注的系統提示
* **控制成本**，將任務路由到更快、更便宜的模型，如 Haiku

Claude 使用每個 subagent 的描述來決定何時委派任務。當您建立 subagent 時，請寫一個清晰的描述，以便 Claude 知道何時使用它。

Claude Code 包括幾個內建 subagents，如 **Explore**、**Plan** 和 **general-purpose**。您也可以建立自訂 subagents 來處理特定任務。本頁涵蓋 [內建 subagents](#built-in-subagents)、[如何建立您自己的](#quickstart-create-your-first-subagent)、[完整配置選項](#configure-subagents)、[使用 subagents 的模式](#work-with-subagents) 和 [範例 subagents](#example-subagents)。

## 內建 subagents

Claude Code 包括內建 subagents，Claude 在適當時會自動使用。每個都繼承父對話的權限，並有額外的工具限制。

<Tabs>
  <Tab title="Explore">
    一個快速、唯讀的代理，針對搜尋和分析程式碼庫進行最佳化。

    * **Model**：Haiku（快速、低延遲）
    * **Tools**：唯讀工具（拒絕存取 Write 和 Edit 工具）
    * **Purpose**：檔案發現、程式碼搜尋、程式碼庫探索

    當 Claude 需要搜尋或理解程式碼庫而不進行更改時，它會委派給 Explore。這樣可以將探索結果保持在主要對話上下文之外。

    當呼叫 Explore 時，Claude 指定一個徹底程度：**quick** 用於目標查詢，**medium** 用於平衡探索，或 **very thorough** 用於全面分析。
  </Tab>

  <Tab title="Plan">
    一個研究代理，在 [plan mode](/zh-TW/common-workflows#use-plan-mode-for-safe-code-analysis) 期間使用，以在呈現計畫之前收集上下文。

    * **Model**：從主要對話繼承
    * **Tools**：唯讀工具（拒絕存取 Write 和 Edit 工具）
    * **Purpose**：用於規劃的程式碼庫研究

    當您處於 plan mode 且 Claude 需要理解您的程式碼庫時，它會將研究委派給 Plan subagent。這樣可以防止無限嵌套（subagents 無法產生其他 subagents），同時仍然收集必要的上下文。
  </Tab>

  <Tab title="General-purpose">
    一個能力強大的代理，用於需要探索和行動的複雜多步驟任務。

    * **Model**：從主要對話繼承
    * **Tools**：所有工具
    * **Purpose**：複雜研究、多步驟操作、程式碼修改

    當任務需要探索和修改、複雜推理來解釋結果或多個相依步驟時，Claude 會委派給 general-purpose。
  </Tab>

  <Tab title="Other">
    Claude Code 包括用於特定任務的其他輔助代理。這些通常會自動呼叫，因此您不需要直接使用它們。

    | Agent             | Model  | Claude 何時使用它                 |
    | :---------------- | :----- | :--------------------------- |
    | statusline-setup  | Sonnet | 當您執行 `/statusline` 來配置您的狀態行時 |
    | Claude Code Guide | Haiku  | 當您提出有關 Claude Code 功能的問題時    |
  </Tab>
</Tabs>

除了這些內建 subagents 之外，您可以建立自己的 subagents，具有自訂提示、工具限制、權限模式、hooks 和 skills。以下部分展示如何開始和自訂 subagents。

## 快速入門：建立您的第一個 subagent

Subagents 在 Markdown 檔案中定義，具有 YAML frontmatter。您可以 [手動建立它們](#write-subagent-files) 或使用 `/agents` 命令。

本逐步指南將引導您使用 `/agents` 命令建立使用者層級的 subagent。該 subagent 審查程式碼並為程式碼庫提出改進建議。

<Steps>
  <Step title="開啟 subagents 介面">
    在 Claude Code 中，執行：

    ```text  theme={null}
    /agents
    ```
  </Step>

  <Step title="選擇位置">
    選擇 **Create new agent**，然後選擇 **Personal**。這會將 subagent 儲存到 `~/.claude/agents/`，以便在所有專案中使用。
  </Step>

  <Step title="使用 Claude 生成">
    選擇 **Generate with Claude**。出現提示時，描述 subagent：

    ```text  theme={null}
    A code improvement agent that scans files and suggests improvements
    for readability, performance, and best practices. It should explain
    each issue, show the current code, and provide an improved version.
    ```

    Claude 為您生成識別碼、描述和系統提示。
  </Step>

  <Step title="選擇工具">
    對於唯讀審查者，取消選擇除 **Read-only tools** 之外的所有內容。如果您保持所有工具選中，subagent 將繼承主要對話可用的所有工具。
  </Step>

  <Step title="選擇模型">
    選擇 subagent 使用的模型。對於此範例代理，選擇 **Sonnet**，它在分析程式碼模式的能力和速度之間取得平衡。
  </Step>

  <Step title="選擇顏色">
    為 subagent 選擇背景顏色。這可以幫助您在 UI 中識別哪個 subagent 正在執行。
  </Step>

  <Step title="配置記憶">
    選擇 **User scope** 為 subagent 提供 [persistent memory directory](#enable-persistent-memory)，位於 `~/.claude/agent-memory/`。Subagent 使用此目錄在對話之間累積見解，例如程式碼庫模式和重複出現的問題。如果您不希望 subagent 保留學習，請選擇 **None**。
  </Step>

  <Step title="儲存並試用">
    檢查配置摘要。按 `s` 或 `Enter` 儲存，或按 `e` 在編輯器中儲存並編輯檔案。Subagent 立即可用。試試看：

    ```text  theme={null}
    Use the code-improver agent to suggest improvements in this project
    ```

    Claude 委派給您的新 subagent，它掃描程式碼庫並返回改進建議。
  </Step>
</Steps>

現在您有一個 subagent，可以在機器上的任何專案中使用它來分析程式碼庫並提出改進建議。

您也可以手動建立 subagents 作為 Markdown 檔案、透過 CLI 標誌定義它們，或透過外掛程式分發它們。以下部分涵蓋所有配置選項。

## 配置 subagents

### 使用 /agents 命令

`/agents` 命令提供用於管理 subagents 的互動式介面。執行 `/agents` 以：

* 檢視所有可用的 subagents（內建、使用者、專案和外掛程式）
* 使用引導式設定或 Claude 生成建立新的 subagents
* 編輯現有 subagent 配置和工具存取
* 刪除自訂 subagents
* 查看當存在重複項時哪些 subagents 處於活動狀態

這是建立和管理 subagents 的建議方式。對於手動建立或自動化，您也可以直接新增 subagent 檔案。

若要從命令行列出所有配置的 subagents 而不啟動互動式工作階段，請執行 `claude agents`。這會按來源分組顯示代理，並指示哪些被更高優先級的定義覆蓋。

### 選擇 subagent 範圍

Subagents 是具有 YAML frontmatter 的 Markdown 檔案。根據範圍將它們儲存在不同位置。當多個 subagents 共享相同名稱時，更高優先級的位置獲勝。

| Location              | Scope     | Priority | 如何建立                                      |
| :-------------------- | :-------- | :------- | :---------------------------------------- |
| 受管設定                  | 組織範圍      | 1（最高）    | 透過 [managed settings](/zh-TW/settings) 部署 |
| `--agents` CLI 標誌     | 目前工作階段    | 2        | 啟動 Claude Code 時傳遞 JSON                   |
| `.claude/agents/`     | 目前專案      | 3        | 互動式或手動                                    |
| `~/.claude/agents/`   | 所有您的專案    | 4        | 互動式或手動                                    |
| Plugin 的 `agents/` 目錄 | 啟用外掛程式的位置 | 5（最低）    | 使用 [plugins](/zh-TW/plugins) 安裝           |

**專案 subagents**（`.claude/agents/`）非常適合特定於程式碼庫的 subagents。將它們簽入版本控制，以便您的團隊可以協作使用和改進它們。

專案 subagents 是透過從目前工作目錄向上走來發現的。使用 `--add-dir` 新增的目錄 [僅授予檔案存取權限](/zh-TW/permissions#additional-directories-grant-file-access-not-configuration)，不會掃描 subagents。若要跨專案共享 subagents，請使用 `~/.claude/agents/` 或 [plugin](/zh-TW/plugins)。

**使用者 subagents**（`~/.claude/agents/`）是在所有專案中可用的個人 subagents。

**CLI 定義的 subagents** 在啟動 Claude Code 時作為 JSON 傳遞。它們僅存在於該工作階段，不會儲存到磁碟，使其適用於快速測試或自動化指令碼。您可以在單一 `--agents` 呼叫中定義多個 subagents：

```bash  theme={null}
claude --agents '{
  "code-reviewer": {
    "description": "Expert code reviewer. Use proactively after code changes.",
    "prompt": "You are a senior code reviewer. Focus on code quality, security, and best practices.",
    "tools": ["Read", "Grep", "Glob", "Bash"],
    "model": "sonnet"
  },
  "debugger": {
    "description": "Debugging specialist for errors and test failures.",
    "prompt": "You are an expert debugger. Analyze errors, identify root causes, and provide fixes."
  }
}'
```

`--agents` 標誌接受 JSON，具有與基於檔案的 subagents 相同的 [frontmatter](#supported-frontmatter-fields) 欄位：`description`、`prompt`、`tools`、`disallowedTools`、`model`、`permissionMode`、`mcpServers`、`hooks`、`maxTurns`、`skills`、`initialPrompt`、`memory`、`effort`、`background`、`isolation` 和 `color`。使用 `prompt` 作為系統提示，等同於基於檔案的 subagents 中的 markdown 主體。

**受管 subagents** 由組織管理員部署。將 markdown 檔案放在 [managed settings directory](/zh-TW/settings#settings-files) 內的 `.claude/agents/` 中，使用與專案和使用者 subagents 相同的 frontmatter 格式。受管定義優先於具有相同名稱的專案和使用者 subagents。

**外掛程式 subagents** 來自您已安裝的 [plugins](/zh-TW/plugins)。它們與您的自訂 subagents 一起出現在 `/agents` 中。請參閱 [外掛程式元件參考](/zh-TW/plugins-reference#agents) 以了解建立外掛程式 subagents 的詳細資訊。

<Note>
  基於安全考慮，外掛程式 subagents 不支援 `hooks`、`mcpServers` 或 `permissionMode` frontmatter 欄位。從外掛程式載入代理時，這些欄位會被忽略。如果您需要它們，請將代理檔案複製到 `.claude/agents/` 或 `~/.claude/agents/`。您也可以在 `settings.json` 或 `settings.local.json` 中的 [`permissions.allow`](/zh-TW/settings#permission-settings) 新增規則，但這些規則適用於整個工作階段，而不僅僅是外掛程式 subagent。
</Note>

來自任何這些範圍的 subagent 定義也可用於 [agent teams](/zh-TW/agent-teams#use-subagent-definitions-for-teammates)：當產生隊友時，您可以參考 subagent 類型，隊友會繼承其系統提示、工具和模型。

### 編寫 subagent 檔案

Subagent 檔案使用 YAML frontmatter 進行配置，後面跟著 Markdown 中的系統提示：

<Note>
  Subagents 在工作階段開始時載入。如果您透過手動新增檔案來建立 subagent，請重新啟動您的工作階段或使用 `/agents` 立即載入它。
</Note>

```markdown  theme={null}
---
name: code-reviewer
description: Reviews code for quality and best practices
tools: Read, Glob, Grep
model: sonnet
---

You are a code reviewer. When invoked, analyze the code and provide
specific, actionable feedback on quality, security, and best practices.
```

Frontmatter 定義 subagent 的中繼資料和配置。主體成為指導 subagent 行為的系統提示。Subagents 只接收此系統提示（加上基本環境詳細資訊，如工作目錄），而不是完整的 Claude Code 系統提示。

#### 支援的 frontmatter 欄位

以下欄位可用於 YAML frontmatter。只有 `name` 和 `description` 是必需的。

| Field             | Required | Description                                                                                                                                                                   |
| :---------------- | :------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `name`            | Yes      | 使用小寫字母和連字號的唯一識別碼                                                                                                                                                              |
| `description`     | Yes      | Claude 何時應委派給此 subagent                                                                                                                                                       |
| `tools`           | No       | [Tools](#available-tools) subagent 可以使用。如果省略，繼承所有工具                                                                                                                           |
| `disallowedTools` | No       | 要拒絕的工具，從繼承或指定的清單中移除                                                                                                                                                           |
| `model`           | No       | [Model](#choose-a-model) 使用：`sonnet`、`opus`、`haiku`、完整模型 ID（例如，`claude-opus-4-6`）或 `inherit`。預設為 `inherit`                                                                    |
| `permissionMode`  | No       | [Permission mode](#permission-modes)：`default`、`acceptEdits`、`auto`、`dontAsk`、`bypassPermissions` 或 `plan`                                                                    |
| `maxTurns`        | No       | subagent 停止前的最大代理轉數                                                                                                                                                           |
| `skills`          | No       | [Skills](/zh-TW/skills) 在啟動時載入到 subagent 的上下文中。注入完整技能內容，而不僅僅是可供呼叫。Subagents 不從父對話繼承技能                                                                                         |
| `mcpServers`      | No       | [MCP servers](/zh-TW/mcp) 可用於此 subagent。每個條目要麼是參考已配置伺服器的伺服器名稱（例如，`"slack"`），要麼是內聯定義，其中伺服器名稱為鍵，完整 [MCP server config](/zh-TW/mcp#installing-mcp-servers) 為值                    |
| `hooks`           | No       | [Lifecycle hooks](#define-hooks-for-subagents) 限定於此 subagent                                                                                                                  |
| `memory`          | No       | [Persistent memory scope](#enable-persistent-memory)：`user`、`project` 或 `local`。啟用跨工作階段學習                                                                                     |
| `background`      | No       | 設定為 `true` 以始終將此 subagent 作為 [background task](#run-subagents-in-foreground-or-background) 執行。預設：`false`                                                                      |
| `effort`          | No       | 此 subagent 活動時的努力程度。覆蓋工作階段努力程度。預設：從工作階段繼承。選項：`low`、`medium`、`high`、`max`（僅 Opus 4.6）                                                                                          |
| `isolation`       | No       | 設定為 `worktree` 以在臨時 [git worktree](/zh-TW/common-workflows#run-parallel-claude-code-sessions-with-git-worktrees) 中執行 subagent，為其提供儲存庫的隔離副本。如果 subagent 不進行任何更改，worktree 會自動清理 |
| `color`           | No       | Subagent 在任務清單和文字中的顯示顏色。接受 `red`、`blue`、`green`、`yellow`、`purple`、`orange`、`pink` 或 `cyan`                                                                                    |
| `initialPrompt`   | No       | 當此代理作為主工作階段代理執行時（透過 `--agent` 或 `agent` 設定），自動提交為第一個使用者轉數。[Commands](/zh-TW/commands) 和 [skills](/zh-TW/skills) 會被處理。前置於任何使用者提供的提示                                            |

### 選擇模型

`model` 欄位控制 subagent 使用的 [AI model](/zh-TW/model-config)：

* **Model alias**：使用可用的別名之一：`sonnet`、`opus` 或 `haiku`
* **Full model ID**：使用完整模型 ID，例如 `claude-opus-4-6` 或 `claude-sonnet-4-6`。接受與 `--model` 標誌相同的值
* **inherit**：使用與主要對話相同的模型
* **Omitted**：如果未指定，預設為 `inherit`（使用與主要對話相同的模型）

當 Claude 呼叫 subagent 時，它也可以為該特定呼叫傳遞 `model` 參數。Claude Code 按此順序解析 subagent 的模型：

1. [`CLAUDE_CODE_SUBAGENT_MODEL`](/zh-TW/model-config#environment-variables) 環境變數（如果設定）
2. 每次呼叫的 `model` 參數
3. Subagent 定義的 `model` frontmatter
4. 主要對話的模型

### 控制 subagent 功能

您可以透過工具存取、權限模式和條件規則來控制 subagents 可以執行的操作。

#### 可用工具

Subagents 可以使用 Claude Code 的任何 [internal tools](/zh-TW/tools-reference)。預設情況下，subagents 從主要對話繼承所有工具，包括 MCP 工具。

若要限制工具，請使用 `tools` 欄位（允許清單）或 `disallowedTools` 欄位（拒絕清單）。此範例使用 `tools` 來專門允許 Read、Grep、Glob 和 Bash。Subagent 無法編輯檔案、寫入檔案或使用任何 MCP 工具：

```yaml  theme={null}
---
name: safe-researcher
description: Research agent with restricted capabilities
tools: Read, Grep, Glob, Bash
---
```

此範例使用 `disallowedTools` 來繼承主要對話中的每個工具，除了 Write 和 Edit。Subagent 保留 Bash、MCP 工具和其他所有內容：

```yaml  theme={null}
---
name: no-writes
description: Inherits every tool except file writes
disallowedTools: Write, Edit
---
```

如果兩者都設定，`disallowedTools` 首先應用，然後 `tools` 針對剩餘的池進行解析。同時列在兩者中的工具會被移除。

#### 限制可以產生的 subagents

當代理以 `claude --agent` 作為主執行緒執行時，它可以使用 Agent 工具產生 subagents。若要限制它可以產生的 subagent 類型，請在 `tools` 欄位中使用 `Agent(agent_type)` 語法。

<Note>在版本 2.1.63 中，Task 工具已重新命名為 Agent。設定和代理定義中的現有 `Task(...)` 參考仍然作為別名工作。</Note>

```yaml  theme={null}
---
name: coordinator
description: Coordinates work across specialized agents
tools: Agent(worker, researcher), Read, Bash
---
```

這是一個允許清單：只有 `worker` 和 `researcher` subagents 可以產生。如果代理嘗試產生任何其他類型，請求失敗，代理在其提示中只看到允許的類型。若要在允許所有其他類型的同時阻止特定代理，請改用 [`permissions.deny`](#disable-specific-subagents)。

若要允許產生任何 subagent 而不受限制，請使用不帶括號的 `Agent`：

```yaml  theme={null}
tools: Agent, Read, Bash
```

如果 `Agent` 完全從 `tools` 清單中省略，代理無法產生任何 subagents。此限制僅適用於以 `claude --agent` 作為主執行緒執行的代理。Subagents 無法產生其他 subagents，因此 `Agent(agent_type)` 在 subagent 定義中無效。

#### 將 MCP 伺服器限定於 subagent

使用 `mcpServers` 欄位為 subagent 提供對主要對話中不可用的 [MCP](/zh-TW/mcp) 伺服器的存取。此處定義的內聯伺服器在 subagent 啟動時連接，在完成時斷開連接。字串參考共享父工作階段的連接。

清單中的每個條目要麼是內聯伺服器定義，要麼是參考工作階段中已配置的 MCP 伺服器的字串：

```yaml  theme={null}
---
name: browser-tester
description: Tests features in a real browser using Playwright
mcpServers:
  # Inline definition: scoped to this subagent only
  - playwright:
      type: stdio
      command: npx
      args: ["-y", "@playwright/mcp@latest"]
  # Reference by name: reuses an already-configured server
  - github
---

Use the Playwright tools to navigate, screenshot, and interact with pages.
```

內聯定義使用與 `.mcp.json` 伺服器條目相同的架構（`stdio`、`http`、`sse`、`ws`），由伺服器名稱鍵入。

若要將 MCP 伺服器保持在主要對話之外，並避免其工具描述在那裡消耗上下文，請在此處內聯定義它，而不是在 `.mcp.json` 中。Subagent 獲得工具；父對話不獲得。

#### 權限模式

`permissionMode` 欄位控制 subagent 如何處理權限提示。Subagents 從主要對話繼承權限上下文，並可以覆蓋模式，除非父模式優先，如下所述。

| Mode                | Behavior                                                                             |
| :------------------ | :----------------------------------------------------------------------------------- |
| `default`           | 標準權限檢查，帶有提示                                                                          |
| `acceptEdits`       | 自動接受檔案編輯                                                                             |
| `auto`              | [Auto mode](/zh-TW/permission-modes#eliminate-prompts-with-auto-mode)：AI 分類器評估每個工具呼叫 |
| `dontAsk`           | 自動拒絕權限提示（明確允許的工具仍然工作）                                                                |
| `bypassPermissions` | 跳過權限提示                                                                               |
| `plan`              | Plan mode（唯讀探索）                                                                      |

<Warning>
  謹慎使用 `bypassPermissions`。它跳過權限提示，允許 subagent 執行操作而無需批准。寫入 `.git`、`.claude`、`.vscode` 和 `.idea` 目錄仍然會提示確認，除了 `.claude/commands`、`.claude/agents` 和 `.claude/skills`。請參閱 [permission modes](/zh-TW/permission-modes#skip-all-checks-with-bypasspermissions-mode) 以了解詳細資訊。
</Warning>

如果父級使用 `bypassPermissions`，這優先並且無法被覆蓋。如果父級使用 [auto mode](/zh-TW/permission-modes#eliminate-prompts-with-auto-mode)，subagent 繼承 auto mode，其 frontmatter 中的任何 `permissionMode` 都會被忽略：分類器使用與父工作階段相同的阻止和允許規則評估 subagent 的工具呼叫。

#### 將技能預載入 subagents

使用 `skills` 欄位在啟動時將技能內容注入到 subagent 的上下文中。這為 subagent 提供領域知識，而無需在執行期間發現和載入技能。

```yaml  theme={null}
---
name: api-developer
description: Implement API endpoints following team conventions
skills:
  - api-conventions
  - error-handling-patterns
---

Implement API endpoints. Follow the conventions and patterns from the preloaded skills.
```

每個技能的完整內容被注入到 subagent 的上下文中，而不僅僅是可供呼叫。Subagents 不從父對話繼承技能；您必須明確列出它們。

<Note>
  這與 [在 subagent 中執行技能](/zh-TW/skills#run-skills-in-a-subagent) 相反。使用 subagent 中的 `skills`，subagent 控制系統提示並載入技能內容。使用技能中的 `context: fork`，技能內容被注入到您指定的代理中。兩者都使用相同的基礎系統。
</Note>

#### 啟用持久記憶

`memory` 欄位為 subagent 提供一個在對話之間存活的持久目錄。Subagent 使用此目錄隨著時間建立知識，例如程式碼庫模式、除錯見解和架構決策。

```yaml  theme={null}
---
name: code-reviewer
description: Reviews code for quality and best practices
memory: user
---

You are a code reviewer. As you review code, update your agent memory with
patterns, conventions, and recurring issues you discover.
```

根據記憶應該應用的廣泛程度選擇範圍：

| Scope     | Location                                      | 使用時機                          |
| :-------- | :-------------------------------------------- | :---------------------------- |
| `user`    | `~/.claude/agent-memory/<name-of-agent>/`     | subagent 應該記住跨所有專案的學習         |
| `project` | `.claude/agent-memory/<name-of-agent>/`       | subagent 的知識是特定於專案的，可透過版本控制共享 |
| `local`   | `.claude/agent-memory-local/<name-of-agent>/` | subagent 的知識是特定於專案的，但不應簽入版本控制 |

啟用記憶時：

* Subagent 的系統提示包括讀取和寫入記憶目錄的說明。
* Subagent 的系統提示還包括記憶目錄中 `MEMORY.md` 的前 200 行或 25KB（以先到者為準），以及如果超過該限制則策劃 `MEMORY.md` 的說明。
* Read、Write 和 Edit 工具會自動啟用，以便 subagent 可以管理其記憶檔案。

##### 持久記憶提示

* `project` 是建議的預設範圍。它使 subagent 知識可透過版本控制共享。當 subagent 的知識在所有專案中廣泛適用時使用 `user`，或當知識不應簽入版本控制時使用 `local`。
* 要求 subagent 在開始工作前查閱其記憶："Review this PR, and check your memory for patterns you've seen before."
* 要求 subagent 在完成任務後更新其記憶："Now that you're done, save what you learned to your memory." 隨著時間的推移，這會建立一個知識庫，使 subagent 更有效。
* 直接在 subagent 的 markdown 檔案中包括記憶說明，以便它主動維護自己的知識庫：

  ```markdown  theme={null}
  Update your agent memory as you discover codepaths, patterns, library
  locations, and key architectural decisions. This builds up institutional
  knowledge across conversations. Write concise notes about what you found
  and where.
  ```

#### 使用 hooks 的條件規則

為了更動態地控制工具使用，請使用 `PreToolUse` hooks 在執行前驗證操作。當您需要允許工具的某些操作同時阻止其他操作時，這很有用。

此範例建立一個只允許唯讀資料庫查詢的 subagent。`PreToolUse` hook 在每個 Bash 命令執行前執行 `command` 中指定的指令碼：

```yaml  theme={null}
---
name: db-reader
description: Execute read-only database queries
tools: Bash
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/validate-readonly-query.sh"
---
```

Claude Code [透過 stdin 將 hook 輸入作為 JSON 傳遞](/zh-TW/hooks#pretooluse-input) 給 hook 命令。驗證指令碼讀取此 JSON，提取 Bash 命令，並 [以代碼 2 退出](/zh-TW/hooks#exit-code-2-behavior-per-event) 以阻止寫入操作：

```bash  theme={null}
#!/bin/bash
# ./scripts/validate-readonly-query.sh

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# Block SQL write operations (case-insensitive)
if echo "$COMMAND" | grep -iE '\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE)\b' > /dev/null; then
  echo "Blocked: Only SELECT queries are allowed" >&2
  exit 2
fi

exit 0
```

請參閱 [Hook input](/zh-TW/hooks#pretooluse-input) 以了解完整的輸入架構，以及 [exit codes](/zh-TW/hooks#exit-code-output) 以了解退出代碼如何影響行為。

#### 禁用特定 subagents

您可以透過將 subagents 新增到 [settings](/zh-TW/settings#permission-settings) 中的 `deny` 陣列來防止 Claude 使用特定 subagents。使用格式 `Agent(subagent-name)`，其中 `subagent-name` 與 subagent 的 name 欄位相符。

```json  theme={null}
{
  "permissions": {
    "deny": ["Agent(Explore)", "Agent(my-custom-agent)"]
  }
}
```

這適用於內建和自訂 subagents。您也可以使用 `--disallowedTools` CLI 標誌：

```bash  theme={null}
claude --disallowedTools "Agent(Explore)"
```

請參閱 [Permissions documentation](/zh-TW/permissions#tool-specific-permission-rules) 以了解有關權限規則的更多詳細資訊。

### 為 subagents 定義 hooks

Subagents 可以定義在 subagent 生命週期期間執行的 [hooks](/zh-TW/hooks)。有兩種方式來配置 hooks：

1. **在 subagent 的 frontmatter 中**：定義只在該 subagent 活動時執行的 hooks
2. **在 `settings.json` 中**：定義在 subagents 啟動或停止時在主工作階段中執行的 hooks

#### Subagent frontmatter 中的 Hooks

直接在 subagent 的 markdown 檔案中定義 hooks。這些 hooks 只在該特定 subagent 活動時執行，並在完成時清理。

支援所有 [hook events](/zh-TW/hooks#hook-events)。subagents 最常見的事件是：

| Event         | Matcher input | 何時觸發                                   |
| :------------ | :------------ | :------------------------------------- |
| `PreToolUse`  | Tool name     | 在 subagent 使用工具之前                      |
| `PostToolUse` | Tool name     | 在 subagent 使用工具之後                      |
| `Stop`        | (none)        | 當 subagent 完成時（在執行時轉換為 `SubagentStop`） |

此範例使用 `PreToolUse` hook 驗證 Bash 命令，並在檔案編輯後使用 `PostToolUse` 執行 linter：

```yaml  theme={null}
---
name: code-reviewer
description: Review code changes with automatic linting
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/validate-command.sh $TOOL_INPUT"
  PostToolUse:
    - matcher: "Edit|Write"
      hooks:
        - type: command
          command: "./scripts/run-linter.sh"
---
```

Frontmatter 中的 `Stop` hooks 會自動轉換為 `SubagentStop` 事件。

#### 用於 subagent 事件的專案層級 hooks

在 `settings.json` 中配置 hooks，以回應主工作階段中的 subagent 生命週期事件。

| Event           | Matcher input   | 何時觸發             |
| :-------------- | :-------------- | :--------------- |
| `SubagentStart` | Agent type name | 當 subagent 開始執行時 |
| `SubagentStop`  | Agent type name | 當 subagent 完成時   |

兩個事件都支援匹配器以按名稱針對特定代理類型。此範例僅在 `db-agent` subagent 啟動時執行設定指令碼，並在任何 subagent 停止時執行清理指令碼：

```json  theme={null}
{
  "hooks": {
    "SubagentStart": [
      {
        "matcher": "db-agent",
        "hooks": [
          { "type": "command", "command": "./scripts/setup-db-connection.sh" }
        ]
      }
    ],
    "SubagentStop": [
      {
        "hooks": [
          { "type": "command", "command": "./scripts/cleanup-db-connection.sh" }
        ]
      }
    ]
  }
}
```

請參閱 [Hooks](/zh-TW/hooks) 以了解完整的 hook 配置格式。

## 使用 subagents

### 理解自動委派

Claude 根據您請求中的任務描述、subagent 配置中的 `description` 欄位和目前上下文自動委派任務。為了鼓勵主動委派，在 subagent 的 description 欄位中包括"use proactively"之類的短語。

### 明確呼叫 subagents

當自動委派不夠時，您可以自己要求 subagent。三種模式從一次性建議升級到工作階段範圍的預設：

* **自然語言**：在提示中命名 subagent；Claude 決定是否委派
* **@-mention**：保證 subagent 為一個任務執行
* **工作階段範圍**：整個工作階段使用該 subagent 的系統提示、工具限制和模型，透過 `--agent` 標誌或 `agent` 設定

對於自然語言，沒有特殊語法。命名 subagent，Claude 通常會委派：

```text  theme={null}
Use the test-runner subagent to fix failing tests
Have the code-reviewer subagent look at my recent changes
```

**@-mention subagent。** 輸入 `@` 並從預輸入中選擇 subagent，就像您 @-mention 檔案一樣。這確保該特定 subagent 執行，而不是將選擇留給 Claude：

```text  theme={null}
@"code-reviewer (agent)" look at the auth changes
```

您的完整訊息仍然會傳送給 Claude，它根據您要求的內容為 subagent 編寫任務提示。@-mention 控制 Claude 呼叫哪個 subagent，而不是它接收什麼提示。

由啟用的 [plugin](/zh-TW/plugins) 提供的 Subagents 在預輸入中顯示為 `<plugin-name>:<agent-name>`。名為背景 subagents 目前在工作階段中執行也出現在預輸入中，在名稱旁邊顯示其狀態。您也可以手動輸入提及而不使用選擇器：`@agent-<name>` 用於本地 subagents，或 `@agent-<plugin-name>:<agent-name>` 用於外掛程式 subagents。

**將整個工作階段作為 subagent 執行。** 傳遞 [`--agent <name>`](/zh-TW/cli-reference) 以啟動一個工作階段，其中主執行緒本身採用該 subagent 的系統提示、工具限制和模型：

```bash  theme={null}
claude --agent code-reviewer
```

Subagent 的系統提示完全替換預設 Claude Code 系統提示，就像 [`--system-prompt`](/zh-TW/cli-reference) 一樣。`CLAUDE.md` 檔案和專案記憶仍然透過正常訊息流載入。代理名稱在啟動標題中顯示為 `@<name>`，以便您可以確認它是活動的。

這適用於內建和自訂 subagents，選擇在您恢復工作階段時持續。

對於外掛程式提供的 subagent，傳遞限定名稱：`claude --agent <plugin-name>:<agent-name>`。

若要使其成為專案中每個工作階段的預設值，請在 `.claude/settings.json` 中設定 `agent`：

```json  theme={null}
{
  "agent": "code-reviewer"
}
```

如果兩者都存在，CLI 標誌會覆蓋設定。

### 在前景或背景中執行 subagents

Subagents 可以在前景（阻止）或背景（並行）中執行：

* **前景 subagents** 阻止主要對話直到完成。權限提示和澄清問題（如 [`AskUserQuestion`](/zh-TW/tools-reference)）會傳遞給您。
* **背景 subagents** 在您繼續工作時並行執行。啟動前，Claude Code 會提示輸入 subagent 需要的任何工具權限，確保它具有必要的批准。執行後，subagent 繼承這些權限並自動拒絕任何未預先批准的內容。如果背景 subagent 需要提出澄清問題，該工具呼叫失敗，但 subagent 繼續。

如果背景 subagent 因權限遺失而失敗，您可以啟動一個新的前景 subagent 執行相同任務以使用互動式提示重試。

Claude 根據任務決定是否在前景或背景中執行 subagents。您也可以：

* 要求 Claude "run this in the background"
* 按 **Ctrl+B** 將執行中的任務放在背景中

若要禁用所有背景任務功能，請將 `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS` 環境變數設定為 `1`。請參閱 [Environment variables](/zh-TW/env-vars)。

### 常見模式

#### 隔離高容量操作

subagents 最有效的用途之一是隔離產生大量輸出的操作。執行測試、獲取文件或處理日誌檔案可能會消耗大量上下文。透過將這些委派給 subagent，詳細輸出保留在 subagent 的上下文中，而只有相關摘要返回到主要對話。

```text  theme={null}
Use a subagent to run the test suite and report only the failing tests with their error messages
```

#### 執行並行研究

對於獨立調查，產生多個 subagents 以同時工作：

```text  theme={null}
Research the authentication, database, and API modules in parallel using separate subagents
```

每個 subagent 獨立探索其領域，然後 Claude 綜合發現。當研究路徑彼此不相依時，這效果最好。

<Warning>
  當 subagents 完成時，其結果返回到主要對話。執行許多 subagents，每個都返回詳細結果，可能會消耗大量上下文。
</Warning>

對於需要持續並行性或超過上下文視窗的任務，[agent teams](/zh-TW/agent-teams) 為每個工作者提供自己的獨立上下文。

#### 鏈接 subagents

對於多步驟工作流程，要求 Claude 按順序使用 subagents。每個 subagent 完成其任務並將結果返回給 Claude，然後將相關上下文傳遞給下一個 subagent。

```text  theme={null}
Use the code-reviewer subagent to find performance issues, then use the optimizer subagent to fix them
```

### 在 subagents 和主要對話之間選擇

在以下情況下使用 **主要對話**：

* 任務需要頻繁的來回或反覆改進
* 多個階段共享重要上下文（規劃 → 實現 → 測試）
* 您正在進行快速、有針對性的更改
* 延遲很重要。Subagents 從頭開始，可能需要時間收集上下文

在以下情況下使用 **subagents**：

* 任務產生您不需要在主要上下文中的詳細輸出
* 您想強制執行特定的工具限制或權限
* 工作是自包含的，可以返回摘要

當您想要可重複使用的提示或在主要對話上下文中執行的工作流程而不是隔離的 subagent 上下文時，請改為考慮 [Skills](/zh-TW/skills)。

對於關於對話中已有內容的快速問題，請使用 [`/btw`](/zh-TW/interactive-mode#side-questions-with-btw) 而不是 subagent。它看到您的完整上下文，但沒有工具存取，答案被丟棄而不是新增到歷史記錄。

<Note>
  Subagents 無法產生其他 subagents。如果您的工作流程需要嵌套委派，請使用 [Skills](/zh-TW/skills) 或從主要對話 [鏈接 subagents](#chain-subagents)。
</Note>

### 管理 subagent 上下文

#### 恢復 subagents

每個 subagent 呼叫都會建立一個具有新鮮上下文的新實例。若要繼續現有 subagent 的工作而不是重新開始，請要求 Claude 恢復它。

恢復的 subagents 保留其完整對話歷史記錄，包括所有先前的工具呼叫、結果和推理。Subagent 從停止的地方精確繼續，而不是從頭開始。

當 subagent 完成時，Claude 接收其代理 ID。Claude 使用 `SendMessage` 工具，將代理的 ID 作為 `to` 欄位來恢復它。`SendMessage` 工具僅在透過 `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` 啟用 [agent teams](/zh-TW/agent-teams) 時可用。

若要恢復 subagent，請要求 Claude 繼續先前的工作：

```text  theme={null}
Use the code-reviewer subagent to review the authentication module
[Agent completes]

Continue that code review and now analyze the authorization logic
[Claude resumes the subagent with full context from previous conversation]
```

如果停止的 subagent 接收 `SendMessage`，它會自動在背景中恢復，無需新的 `Agent` 呼叫。

您也可以要求 Claude 提供代理 ID，如果您想明確參考它，或在 `~/.claude/projects/{project}/{sessionId}/subagents/` 的文字檔案中找到 ID。每個文字都儲存為 `agent-{agentId}.jsonl`。

Subagent 文字獨立於主要對話持續存在：

* **主要對話壓縮**：當主要對話壓縮時，subagent 文字不受影響。它們儲存在單獨的檔案中。
* **工作階段持續性**：Subagent 文字在其工作階段內持續存在。您可以透過恢復相同工作階段在重新啟動 Claude Code 後 [恢復 subagent](#resume-subagents)。
* **自動清理**：文字根據 `cleanupPeriodDays` 設定進行清理（預設：30 天）。

#### 自動壓縮

Subagents 支援使用與主要對話相同的邏輯進行自動壓縮。預設情況下，自動壓縮在大約 95% 容量時觸發。若要更早觸發壓縮，請將 `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` 設定為較低的百分比（例如，`50`）。請參閱 [environment variables](/zh-TW/env-vars) 以了解詳細資訊。

壓縮事件記錄在 subagent 文字檔案中：

```json  theme={null}
{
  "type": "system",
  "subtype": "compact_boundary",
  "compactMetadata": {
    "trigger": "auto",
    "preTokens": 167189
  }
}
```

`preTokens` 值顯示壓縮發生前使用了多少個 tokens。

## 範例 subagents

這些範例展示了建立 subagents 的有效模式。將它們用作起點，或使用 Claude 生成自訂版本。

<Tip>
  **最佳實踐：**

  * **設計專注的 subagents：** 每個 subagent 應該在一個特定任務上表現出色
  * **寫詳細的描述：** Claude 使用描述來決定何時委派
  * **限制工具存取：** 僅授予必要的權限以確保安全和專注
  * **簽入版本控制：** 與您的團隊共享專案 subagents
</Tip>

### 程式碼審查者

一個唯讀 subagent，審查程式碼而不修改它。此範例展示如何設計一個具有有限工具存取（無 Edit 或 Write）和詳細提示的專注 subagent，該提示明確指定要查找的內容以及如何格式化輸出。

```markdown  theme={null}
---
name: code-reviewer
description: Expert code review specialist. Proactively reviews code for quality, security, and maintainability. Use immediately after writing or modifying code.
tools: Read, Grep, Glob, Bash
model: inherit
---

You are a senior code reviewer ensuring high standards of code quality and security.

When invoked:
1. Run git diff to see recent changes
2. Focus on modified files
3. Begin review immediately

Review checklist:
- Code is clear and readable
- Functions and variables are well-named
- No duplicated code
- Proper error handling
- No exposed secrets or API keys
- Input validation implemented
- Good test coverage
- Performance considerations addressed

Provide feedback organized by priority:
- Critical issues (must fix)
- Warnings (should fix)
- Suggestions (consider improving)

Include specific examples of how to fix issues.
```

### 除錯器

一個可以分析和修復問題的 subagent。與程式碼審查者不同，這個包括 Edit，因為修復錯誤需要修改程式碼。提示提供了從診斷到驗證的清晰工作流程。

```markdown  theme={null}
---
name: debugger
description: Debugging specialist for errors, test failures, and unexpected behavior. Use proactively when encountering any issues.
tools: Read, Edit, Bash, Grep, Glob
---

You are an expert debugger specializing in root cause analysis.

When invoked:
1. Capture error message and stack trace
2. Identify reproduction steps
3. Isolate the failure location
4. Implement minimal fix
5. Verify solution works

Debugging process:
- Analyze error messages and logs
- Check recent code changes
- Form and test hypotheses
- Add strategic debug logging
- Inspect variable states

For each issue, provide:
- Root cause explanation
- Evidence supporting the diagnosis
- Specific code fix
- Testing approach
- Prevention recommendations

Focus on fixing the underlying issue, not the symptoms.
```

### 資料科學家

一個用於資料分析工作的特定領域 subagent。此範例展示如何為典型編碼任務之外的專門工作流程建立 subagents。它明確設定 `model: sonnet` 以進行更有能力的分析。

```markdown  theme={null}
---
name: data-scientist
description: Data analysis expert for SQL queries, BigQuery operations, and data insights. Use proactively for data analysis tasks and queries.
tools: Bash, Read, Write
model: sonnet
---

You are a data scientist specializing in SQL and BigQuery analysis.

When invoked:
1. Understand the data analysis requirement
2. Write efficient SQL queries
3. Use BigQuery command line tools (bq) when appropriate
4. Analyze and summarize results
5. Present findings clearly

Key practices:
- Write optimized SQL queries with proper filters
- Use appropriate aggregations and joins
- Include comments explaining complex logic
- Format results for readability
- Provide data-driven recommendations

For each analysis:
- Explain the query approach
- Document any assumptions
- Highlight key findings
- Suggest next steps based on data

Always ensure queries are efficient and cost-effective.
```

### 資料庫查詢驗證器

一個允許 Bash 存取但驗證命令以僅允許唯讀 SQL 查詢的 subagent。此範例展示如何在需要比 `tools` 欄位提供的更精細控制時使用 `PreToolUse` hooks。

```markdown  theme={null}
---
name: db-reader
description: Execute read-only database queries. Use when analyzing data or generating reports.
tools: Bash
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/validate-readonly-query.sh"
---

You are a database analyst with read-only access. Execute SELECT queries to answer questions about the data.

When asked to analyze data:
1. Identify which tables contain the relevant data
2. Write efficient SELECT queries with appropriate filters
3. Present results clearly with context

You cannot modify data. If asked to INSERT, UPDATE, DELETE, or modify schema, explain that you only have read access.
```

Claude Code [透過 stdin 將 hook 輸入作為 JSON 傳遞](/zh-TW/hooks#pretooluse-input) 給 hook 命令。驗證指令碼讀取此 JSON，提取正在執行的命令，並根據 SQL 寫入操作清單檢查它。如果檢測到寫入操作，指令碼 [以代碼 2 退出](/zh-TW/hooks#exit-code-2-behavior-per-event) 以阻止執行並透過 stderr 向 Claude 返回錯誤訊息。

在專案中的任何位置建立驗證指令碼。路徑必須與 hook 配置中的 `command` 欄位相符：

```bash  theme={null}
#!/bin/bash
# Blocks SQL write operations, allows SELECT queries

# Read JSON input from stdin
INPUT=$(cat)

# Extract the command field from tool_input using jq
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

if [ -z "$COMMAND" ]; then
  exit 0
fi

# Block write operations (case-insensitive)
if echo "$COMMAND" | grep -iE '\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|REPLACE|MERGE)\b' > /dev/null; then
  echo "Blocked: Write operations not allowed. Use SELECT queries only." >&2
  exit 2
fi

exit 0
```

使指令碼可執行：

```bash  theme={null}
chmod +x ./scripts/validate-readonly-query.sh
```

Hook 透過 stdin 接收 JSON，Bash 命令在 `tool_input.command` 中。退出代碼 2 阻止操作並將錯誤訊息反饋給 Claude。請參閱 [Hooks](/zh-TW/hooks#exit-code-output) 以了解退出代碼詳細資訊，以及 [Hook input](/zh-TW/hooks#pretooluse-input) 以了解完整的輸入架構。

## 後續步驟

現在您理解了 subagents，請探索這些相關功能：

* [使用外掛程式分發 subagents](/zh-TW/plugins) 以跨團隊或專案共享 subagents
* [以程式方式執行 Claude Code](/zh-TW/headless) 使用 Agent SDK 進行 CI/CD 和自動化
* [使用 MCP 伺服器](/zh-TW/mcp) 為 subagents 提供對外部工具和資料的存取
