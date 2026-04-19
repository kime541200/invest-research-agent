---
name: "Resources: Add YouTube Channel"
description: "Add a YouTube channel to resources.yaml by analyzing recent videos and initializing channel_state"
category: Project
tags: [resources, youtube, routing, mcp]
---

Add a YouTube channel to `resources.yaml` and initialize its `channel_state` entry.

Prefer following the shared `resources-add` skill in `.claude/skills/resources-add/SKILL.md`.

**Input**: The argument after this command is a channel URL, handle, channel name, or a short block of channel info.

---

## Goal

Given new channel information from the user, do all of the following:

1. Resolve the target YouTube channel.
2. Inspect recent videos through `yt-mcp-server`.
3. Infer a practical initial metadata set for this project.
4. Update `resources.yaml` safely.
5. Report what was added and what the user may want to refine.

---

## Required workflow

### 1. Understand the target channel

Use the user input as `<channel_info>`.

If the input is missing or too vague, ask the user to provide one of:
- channel URL
- `@handle`
- channel name

Do not edit `resources.yaml` until the target channel is unambiguous.

### 2. Resolve channel identity with MCP

Use `yt-mcp-server` tools to identify the channel and fetch enough context to classify it.

Preferred flow:
- search channels from the provided handle / URL / name
- confirm the resolved channel id
- list about 5 recent videos
- use titles and channel metadata as the primary basis for classification

### 3. Infer an initial config for this repo

Prepare a new entry under `yt_channels` using this shape:

```yaml
<channel_key>:
  url: <channel url>
  alias: []
  tags: ["tag1", "tag2"]
  topic_keywords: ["keyword1", "keyword2"]
  description: <short summary>
  watch_tier: normal
  priority: 0
```

Also prepare a matching entry under `channel_state`:

```yaml
<channel_key>:
  last_checked_video_title: ""
  channel_id: <resolved channel id>
```

### 4. Classification rules

When inferring values:

- `channel_key`
  - Prefer the YouTube handle without `@` when available.
  - Otherwise use a short stable ASCII identifier derived from the channel name.
  - Keep it lowercase if practical and avoid spaces.

- `tags`
  - Choose 3 to 5 broad routing labels suitable for topic matching in this repo.
  - Prefer reusable domain labels over overly specific phrases.

- `topic_keywords`
  - Choose 3 to 8 more specific keywords or phrases that improve topic routing.
  - Use phrases actually supported by the recent video themes.

- `description`
  - Write 1 short sentence summarizing what the channel mainly covers.

- `watch_tier`
  - Default to `normal` unless the user explicitly indicates a stronger or weaker preference.

- `priority`
  - Default to `0` unless the user explicitly asks for a higher or lower priority.

- `alias`
  - Include obvious alternative names only when they are genuinely useful for matching.

Be conservative. The goal is a solid initial draft, not perfect taxonomy.

### 5. Update `resources.yaml`

Read the existing `resources.yaml` first.

Then update:
- `yt_channels.<channel_key>`
- `channel_state.<channel_key>`

Rules:
- Preserve existing YAML structure and indentation.
- Do not modify unrelated channels.
- If the channel already exists, do not silently overwrite it. Report the existing entry and ask whether to update it.
- If the nearest existing entry uses a richer schema than expected, match the current project schema.

### 6. Report back

After writing the file, give a concise report containing:
- channel name
- resolved URL
- chosen `channel_key`
- inferred `tags`
- inferred `topic_keywords`
- chosen `watch_tier`
- whether `channel_state.channel_id` was initialized

End by telling the user they can ask you to refine:
- tags
- topic_keywords
- watch_tier
- priority
- alias

---

## Guardrails

- Use `yt-mcp-server` as the source for channel/video inspection.
- Do not invent channel metadata without checking MCP results first.
- Do not add fields not already used by this project unless the file clearly shows a newer schema.
- Do not touch note, transcript, or analysis artifacts in this command.
- Do not batch-add multiple channels unless the user explicitly asked for that.
