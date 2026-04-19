---
name: resources-add
description: Add a YouTube channel to `resources.yaml` by resolving the channel with `yt-mcp-server`, inspecting recent videos, inferring initial routing metadata, and safely initializing `channel_state`.
---

# Resources Add

Use this skill when the user wants to add one YouTube channel into `resources.yaml`.

Input can be:
- channel URL
- `@handle`
- channel name
- a short block of channel info

## Workflow

1. Resolve the target channel first.
If the target is ambiguous, ask for a URL, `@handle`, or exact channel name before editing files.

2. Use `yt-mcp-server` as the source of truth.
Preferred flow:
- search the channel from the provided URL / handle / name
- confirm the resolved `channel_id`
- inspect about 5 recent videos
- use channel metadata and recent video titles as the basis for classification

3. Infer an initial config for this repo.
Write one entry under `yt_channels`:

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

Write one matching entry under `channel_state`:

```yaml
<channel_key>:
  last_checked_video_title: ""
  channel_id: <resolved channel id>
```

4. Apply these classification rules conservatively.
- `channel_key`: prefer the YouTube handle without `@`; otherwise derive a short stable ASCII identifier from the channel name
- `tags`: choose 3 to 5 broad reusable routing labels
- `topic_keywords`: choose 3 to 8 more specific phrases supported by recent video themes
- `description`: one short sentence
- `watch_tier`: default to `normal` unless the user explicitly asks otherwise
- `priority`: default to `0` unless the user explicitly asks otherwise
- `alias`: include only useful alternative names

5. Update `resources.yaml` surgically.
- read existing `resources.yaml` first
- update only `yt_channels.<channel_key>` and `channel_state.<channel_key>`
- preserve existing YAML structure and indentation
- do not modify unrelated channels
- if the channel already exists, do not silently overwrite; report it and ask whether to update
- if nearby entries show a richer schema, match the current project schema

6. Report back concisely.
Include:
- channel name
- resolved URL
- chosen `channel_key`
- inferred `tags`
- inferred `topic_keywords`
- chosen `watch_tier`
- whether `channel_state.channel_id` was initialized

End by telling the user they can refine `tags`, `topic_keywords`, `watch_tier`, `priority`, or `alias`.

## Guardrails

- Use `yt-mcp-server` for channel and recent-video inspection.
- Do not invent metadata before checking MCP results.
- Do not add fields not already used by this project unless `resources.yaml` clearly uses a newer schema.
- Do not touch note, transcript, or analysis artifacts.
- Do not batch-add multiple channels unless the user explicitly asked for that.
