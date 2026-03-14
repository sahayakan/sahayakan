# Settings Page

The Settings page manages repositories, Jira projects, and GitHub App configuration.

## Repositories

Add repositories that Sahayakan should analyze.

**Adding a repository:**

1. Click **Add Repository**
2. Fill in:
   - **Name** — Display name
   - **URL** — Full GitHub URL (e.g., `https://github.com/myorg/my-project`)
   - **Provider** — `github`, `gitlab`, or `bitbucket`
   - **Default Branch** — Usually `main`
3. Click **Save**

**Editing and deleting** — Use the edit/delete icons on each row.

## Jira Projects

Connect Jira projects for ticket ingestion.

**Adding a Jira project:**

1. Click **Add Jira Project**
2. Fill in:
   - **Name** — Display name
   - **Project Key** — Jira project key (e.g., `PROJ`)
   - **Base URL** — Your Jira instance URL
3. Click **Save**

!!! note
    Jira integration also requires `JIRA_URL`, `JIRA_EMAIL`, and `JIRA_API_TOKEN` environment variables.

## GitHub Integration

Manage GitHub App configuration for repository access.

**Adding a GitHub App:**

1. Click **Add GitHub App**
2. Enter the App ID, name, private key (PEM), and webhook secret
3. Click **Save**
4. Add installations using the **Add Installation** button

**Testing the connection** — Click **Test** to verify credentials are valid.

See [GitHub App Integration](../integrations/github-app.md) for detailed setup instructions.
