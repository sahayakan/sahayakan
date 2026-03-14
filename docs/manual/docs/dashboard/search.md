# Search Page

The Search page provides semantic search across the entire knowledge base using pgvector embeddings.

## How It Works

Sahayakan embeds all ingested data (issues, PRs, Jira tickets, reports) as vectors in PostgreSQL. When you search, your query is converted to a vector and compared against all stored embeddings using cosine similarity.

## Using Search

1. Enter a natural language query (e.g., "authentication failures in login flow")
2. Optionally filter by source type: issues, PRs, Jira tickets, or reports
3. Results are ranked by semantic similarity

Each result shows:

- **Similarity score** — How closely it matches (0.0-1.0)
- **Source type** — What kind of content it is
- **Title/Summary** — Key identifying information
- **Link** — Click to view the full content

## CLI Access

```bash
# Search across everything
python3 -m cli.main knowledge search "authentication failures"

# Filter by type
python3 -m cli.main knowledge search "deployment issues" --type issue --type pr

# Check embedding stats
python3 -m cli.main knowledge stats
```

!!! tip
    Search works best with descriptive natural language queries rather than keywords. For example, "PRs that changed database schema" will find more relevant results than just "database".
