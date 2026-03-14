# Slack Digest Agent

The Slack Digest agent processes Slack channel messages and produces a summary of key discussions, decisions, and action items.

## Input

| Parameter | Type | Description |
|-----------|------|-------------|
| `channel_name` | string | Slack channel to summarize |

## What It Does

1. Loads ingested Slack messages from the knowledge cache
2. Groups messages by thread and topic
3. Analyzes discussions with the LLM
4. Produces a digest highlighting important items

## Output

| Field | Description |
|-------|-------------|
| `key_discussions` | Important conversations and their summaries |
| `decisions` | Decisions made in the channel |
| `action_items` | Action items mentioned |
| `mentions` | Key people and topics mentioned |

## Prerequisites

Slack messages must be ingested first. See [Slack Integration](../integrations/slack.md).

## Running

```bash
# Sync a Slack channel
curl -X POST http://localhost:8000/ingestion/slack/sync \
  -H "Content-Type: application/json" \
  -d '{"channel_id": "C1234567", "channel_name": "engineering"}'

# Run the digest agent
python3 -m cli.main run slack-digest --param channel_name=engineering
```

## Report Location

```
knowledge-cache/agent_outputs/slack_digest/{channel_name}.json
knowledge-cache/agent_outputs/slack_digest/{channel_name}.md
```
