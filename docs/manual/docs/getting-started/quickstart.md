# Quick Start

This guide walks you through running your first agent after installation.

## 1. Configure a GitHub App

Before syncing GitHub data, you need a GitHub App. See [GitHub App Integration](../integrations/github-app.md) for full setup instructions.

Once configured, add it in **Settings > GitHub Integration** in the web dashboard.

## 2. Add a Repository

In the web dashboard, go to **Settings > Repositories** and add your repository with its GitHub URL.

Or via the API:

```bash
curl -X POST http://localhost:8000/repositories \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-project",
    "url": "https://github.com/myorg/my-project",
    "provider": "github",
    "default_branch": "main"
  }'
```

## 3. Sync GitHub Data

Trigger a sync to ingest issues and pull requests:

=== "CLI"

    ```bash
    python3 -m cli.main sync github myorg my-project
    ```

=== "API"

    ```bash
    curl -X POST http://localhost:8000/ingestion/github/sync \
      -H "Content-Type: application/json" \
      -d '{"owner": "myorg", "repo": "my-project"}'
    ```

## 4. Run an Agent

Run the Issue Triage agent on a specific issue:

=== "CLI"

    ```bash
    python3 -m cli.main run issue-triage --issue 42
    ```

=== "API"

    ```bash
    curl -X POST http://localhost:8000/jobs/run \
      -H "Content-Type: application/json" \
      -d '{"agent": "issue-triage", "parameters": {"issue_id": 42}}'
    ```

## 5. View Results

Check the job status and view the generated report:

=== "CLI"

    ```bash
    # List recent jobs
    python3 -m cli.main job list

    # View the report
    python3 -m cli.main report view issue_analysis 42
    ```

=== "Web Dashboard"

    Navigate to **Jobs** to see the running or completed job, then click through to view the full report on the **Reports** page.

## Next Steps

- [Learn about all agents](../agents/overview.md)
- [Set up scheduled automation](../integrations/github-app.md#webhooks)
- [Explore the web dashboard](../dashboard/overview.md)
