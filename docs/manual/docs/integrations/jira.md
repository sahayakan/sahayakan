# Jira Integration

Sahayakan can ingest Jira tickets to provide context for agent analyses.

## Configuration

Set the following environment variables:

| Variable | Description |
|----------|-------------|
| `JIRA_URL` | Your Jira instance URL (e.g., `https://myorg.atlassian.net`) |
| `JIRA_EMAIL` | Email associated with the API token |
| `JIRA_API_TOKEN` | Jira API token ([create one here](https://id.atlassian.com/manage-profile/security/api-tokens)) |

## Adding Jira Projects

In the web dashboard, go to **Settings > Jira Projects** and add your project with its key (e.g., `PROJ`).

Or via the API:

```bash
curl -X POST http://localhost:8000/jira-projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Project",
    "project_key": "PROJ",
    "base_url": "https://myorg.atlassian.net"
  }'
```

## Syncing Tickets

```bash
# Via API
curl -X POST http://localhost:8000/ingestion/jira/sync \
  -H "Content-Type: application/json" \
  -d '{"project_key": "PROJ"}'

# Check sync status
curl http://localhost:8000/ingestion/jira/status
```

## How Agents Use Jira Data

Jira tickets appear in:

- **Semantic search** results when queries match ticket content
- **PR Context** reports when PRs reference Jira ticket keys
- **Insights** when patterns span both GitHub and Jira data
