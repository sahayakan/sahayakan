# Slack Integration

Sahayakan can ingest Slack channel messages and produce digests of key discussions.

## Configuration

Set the following environment variable:

| Variable | Description |
|----------|-------------|
| `SLACK_BOT_TOKEN` | Slack bot token with `channels:history` and `channels:read` permissions |

## Creating a Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and create a new app
2. Under **OAuth & Permissions**, add bot token scopes:
   - `channels:history` — Read messages
   - `channels:read` — View channel info
3. Install the app to your workspace
4. Copy the **Bot User OAuth Token** (starts with `xoxb-`)

## Syncing Channels

```bash
# Sync a channel
curl -X POST http://localhost:8000/ingestion/slack/sync \
  -H "Content-Type: application/json" \
  -d '{
    "channel_id": "C1234567890",
    "channel_name": "engineering",
    "since_ts": "1704067200.000000"
  }'

# Check sync status
curl http://localhost:8000/ingestion/slack/status
```

The `since_ts` parameter is optional — omit it to sync all available messages.

## Running Slack Digest

After syncing, run the Slack Digest agent:

```bash
python3 -m cli.main run slack-digest --param channel_name=engineering
```

## Notifications

Sahayakan can post agent results back to Slack channels. Configure the notification settings to automatically share triage reports, PR summaries, or insights in relevant channels.
