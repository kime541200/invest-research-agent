---
name: notebooklm-mcp
description: Use this skill when the task needs the project-local NotebookLM MCP server for notebook creation, source ingestion, NotebookLM research, or citation-backed Q&A as part of this repo's topic-driven research workflow.
---

# NotebookLM MCP for invest-research-agent

Use this skill when the current task needs to bring NotebookLM into this repo's workflow.

This is a **project-adapted** skill. It is not for generic NotebookLM automation first; it is for using NotebookLM as a supporting layer inside this repo's topic-driven research process.

## Role in this repo

Keep these boundaries clear:

- `yt-mcp-server` handles YouTube-specific retrieval such as channels, videos, and transcripts.
- `nblm-mcp-server` handles NotebookLM notebooks, source ingestion, NotebookLM-native research, and citation-backed Q&A.
- The main repo workflow still owns topic routing, orchestration, artifact decisions, and final synthesis.

Do not treat NotebookLM as the sole orchestrator of the whole project.

## Before using NotebookLM

Before relying on NotebookLM MCP tools, verify the environment:

1. Confirm the task actually needs NotebookLM.
   Typical cases:
   - ingesting YouTube URLs or web sources into a notebook
   - running NotebookLM research
   - asking citation-backed questions across imported sources
   - using NotebookLM as a research/QA layer after topic routing

2. Confirm NotebookLM authentication is ready.
   Preferred checks:
   - verify `~/.notebooklm/profiles/default/storage_state.json` exists, or
   - from `modules/notebooklm-py/`, run `uv run notebooklm status`

3. Confirm the MCP server is reachable.
   Default endpoint:
   - `http://localhost:8089/mcp`

If the server is not reachable, treat that as an environment issue first. Do not pretend the tools are available.

## Starting the NotebookLM MCP server

When the user asks you to start or restart the NotebookLM MCP server, use the module-local workflow.

From `modules/notebooklm-py/mcp/`:

```bash
uv sync --all-packages
uv run python -m nblm_mcp_server
```

Default transport is HTTP on port `8089`.

Alternative:

```bash
docker compose up -d --build
```

## Recommended workflow in this repo

### 1. Route the topic first

If the user starts from a research topic, do **not** jump straight into NotebookLM.

Prefer the repo's normal entrypoint first:

```bash
python -m invest_research_agent route-topic --topic "[使用者主題]"
```

Use NotebookLM after the topic is clear and the agent knows what evidence it wants to gather.

### 2. Choose the right ingestion path

Use NotebookLM in one of these patterns:

- **Pattern A — YouTube-first**
  - Use `yt-mcp-server` to find the relevant channel/video set
  - add selected video URLs into NotebookLM
  - ask NotebookLM for synthesis and evidence

- **Pattern B — Research enrichment**
  - after a topic is defined, use NotebookLM research to discover web/Drive sources
  - import them into the notebook
  - ask follow-up questions against the imported evidence

- **Pattern C — Mixed evidence notebook**
  - combine YouTube URLs, webpages, and pasted text in one notebook
  - use NotebookLM as the QA layer across all sources

### 3. Manage source readiness explicitly

For one-off source ingestion, `wait=True` is fine.

For asynchronous or batched flows:

1. add source with `wait=False`
2. keep the returned source ID
3. call `get_source_status` or `wait_for_source`
4. only ask NotebookLM questions after the source is ready

### 4. Manage research task state explicitly

When using NotebookLM research:

1. `start_research`
2. `get_research_status` or `wait_for_research`
3. `import_research_sources` if you want the discovered sources inside the notebook
4. `ask_notebook` after sources are ready/imported

If you need a blocking one-shot workflow, `wait_for_research(import_all=True)` is the simplest path.

### 5. Preserve IDs across turns

Always keep track of:

- `notebook_id`
- `source_id` for async source ingestion
- `task_id` for research
- `conversation_id` for multi-turn Q&A

If you ask a follow-up question without passing the prior `conversation_id`, treat it as a new conversation.

## Tool usage rules

### Notebook management

Use:
- `list_notebooks`
- `create_notebook`
- `delete_notebook`

Prefer creating a dedicated notebook for each substantial research topic unless the user explicitly wants to reuse an existing one.

### Source management

Use:
- `add_source`
- `add_youtube_source`
- `add_text_source`
- `list_sources`
- `get_source_status`
- `wait_for_source`
- `get_source_fulltext`
- `delete_source`

Use `get_source_fulltext` when you need the raw indexed text for client-side analysis or verification beyond the NotebookLM answer.

### Research tools

Use:
- `start_research`
- `get_research_status`
- `import_research_sources`
- `wait_for_research`

NotebookLM research is useful for broadening coverage, but it should support the repo workflow rather than replace topic routing.

### Q&A tools

Use:
- `ask_notebook`
- `get_chat_history`
- `save_chat_note`

Always surface citations when they materially support the answer.

## Repo-specific guidance

- Prefer using NotebookLM as a separate research / QA layer instead of directly replacing the transcript pipeline.
- If the user asks for a fully autonomous research flow, keep orchestration in the agent layer and use NotebookLM as one subsystem.
- Do not silently swap a transcript-based workflow for a NotebookLM-based workflow without telling the user.
- If both `yt-mcp-server` and NotebookLM are needed, verify both MCP servers before starting the main run.

## Good output behavior

When reporting NotebookLM-backed findings:

- state what notebook or source set you used
- keep the answer concise
- include citations when available
- distinguish between NotebookLM-derived evidence and your own synthesis

## When not to use this skill

Do not use this skill when:

- the task only needs YouTube metadata or transcripts and does not need NotebookLM
- the task is purely local transcript processing
- the NotebookLM MCP server is not configured and the user has not asked to set it up

## References

If you need lower-level NotebookLM MCP operating details, refer to the upstream materials:

- `modules/notebooklm-py/mcp/skills/nblm-mcp-skill/SKILL.md`
- `modules/notebooklm-py/mcp/skills/nblm-mcp-skill/references/workflows.md`
- `modules/notebooklm-py/mcp/README.md`
