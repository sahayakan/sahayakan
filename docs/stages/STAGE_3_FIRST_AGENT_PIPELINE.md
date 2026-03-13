# Stage 3: First Agent Pipeline

## Goal

Build the Issue Triage Agent end-to-end: GitHub data ingestion, prompt templates, Gemini analysis, report generation, and Git-based storage. After this stage, you have a real working pipeline from GitHub issue to AI-generated analysis report.

## Dependencies

- Stage 2 completed (agent runtime, LLM client, knowledge cache library)

## Tasks

### 3.1 GitHub Data Ingestion Service

`ingestion/github-fetcher/fetcher.py`:

Fetches data from GitHub and stores it in the knowledge cache.

**Data to fetch:**

| Data Type      | API Endpoint                          | Storage Path                            |
| -------------- | ------------------------------------- | --------------------------------------- |
| Issues         | `GET /repos/{owner}/{repo}/issues`    | `knowledge-cache/github/issues/`        |
| Issue comments | `GET /repos/{owner}/{repo}/issues/{n}/comments` | Embedded in issue JSON       |
| Pull requests  | `GET /repos/{owner}/{repo}/pulls`     | `knowledge-cache/github/pull_requests/` |
| PR reviews     | `GET /repos/{owner}/{repo}/pulls/{n}/reviews`    | Embedded in PR JSON          |

**Storage format:**

Each issue stored as `{issue_number}.json`:

```json
{
  "number": 231,
  "title": "Auth service timeout",
  "body": "...",
  "labels": ["bug"],
  "state": "open",
  "comments": [...],
  "created_at": "...",
  "updated_at": "...",
  "fetched_at": "..."
}
```

**Ingestion modes:**

- **Full sync**: Fetch all issues/PRs (initial load)
- **Incremental sync**: Fetch only updated since last sync (uses `since` parameter)

**Configuration:**

```yaml
github:
  token: ${GITHUB_TOKEN}
  repositories:
    - owner: "myorg"
      repo: "myproject"
  sync_interval_minutes: 10
```

**Ingestion commits:**

```
[Ingestion] GitHub sync: 15 issues, 8 PRs updated

Source: GitHub (myorg/myproject)
Timestamp: 2026-03-13T10:00:00Z
Issues: 15 updated
PRs: 8 updated
```

### 3.2 Jira Data Ingestion Service

`ingestion/jira-fetcher/fetcher.py`:

Fetches Jira tickets and stores them in the knowledge cache.

**Data to fetch:**

| Data Type | Storage Path                    |
| --------- | ------------------------------- |
| Tickets   | `knowledge-cache/jira/tickets/` |

**Storage format:**

Each ticket stored as `{ticket_key}.json`:

```json
{
  "key": "PROJ-123",
  "summary": "...",
  "description": "...",
  "status": "In Progress",
  "priority": "High",
  "assignee": "...",
  "labels": [...],
  "comments": [...],
  "fetched_at": "..."
}
```

**Configuration:**

```yaml
jira:
  url: ${JIRA_URL}
  email: ${JIRA_EMAIL}
  token: ${JIRA_API_TOKEN}
  project_keys:
    - "PROJ"
  sync_interval_minutes: 30
```

### 3.3 Issue Triage Agent

`data-plane/agents/issue-triage/agent.py`:

Implements the `BaseAgent` contract.

**load_input:**
- Receives `{"source": "github", "issue_id": 231}` or `{"source": "github", "repo": "myorg/myproject"}` for batch
- Loads issue JSON from knowledge cache

**collect_context:**
- Searches knowledge cache for:
  - Previous issue analyses (to detect duplicates)
  - Related PRs (matching keywords, referenced issues)
  - Jira tickets (if linked via commit messages or issue body)

**analyze:**
- Builds prompt from template
- Sends to Gemini via shared LLM client
- Parses structured JSON response

**generate_output:**

```json
{
  "status": "success",
  "issue_number": 231,
  "summary": "Authentication timeout in OAuth flow",
  "priority": "high",
  "priority_reasoning": "Affects user login flow, multiple reports",
  "is_duplicate": false,
  "possible_duplicates": [198],
  "related_prs": [120, 143],
  "related_jira_tickets": ["PROJ-89"],
  "affected_components": ["auth-service", "oauth-provider"],
  "suggested_labels": ["bug", "auth", "p1"],
  "suggested_actions": [
    "Investigate OAuth token refresh timeout",
    "Check related PR #143 for regression"
  ],
  "confidence": 0.82
}
```

**store_artifacts:**
- Writes report to `knowledge-cache/agent_outputs/issue_analysis/{issue_number}.md`
- Writes raw JSON to `knowledge-cache/agent_outputs/issue_analysis/{issue_number}.json`
- Stores prompt and response in MinIO for audit

### 3.4 Prompt Templates

`data-plane/prompts/issue_analysis.prompt`:

```
You are an expert software engineering assistant analyzing a GitHub issue.

## Issue
Title: {title}
Body: {body}
Labels: {labels}
Comments: {comments}

## Related Context
Previous similar issues: {similar_issues}
Related PRs: {related_prs}
Related Jira tickets: {jira_tickets}

## Instructions
Analyze this issue and provide a JSON response with the following fields:
- priority: "critical", "high", "medium", or "low"
- priority_reasoning: brief explanation
- is_duplicate: true/false
- possible_duplicates: list of issue numbers
- related_prs: list of PR numbers
- related_jira_tickets: list of ticket keys
- affected_components: list of component names
- suggested_labels: list of label suggestions
- suggested_actions: list of recommended next steps
- confidence: 0.0 to 1.0

Respond ONLY with valid JSON. Do not include markdown formatting.
```

### 3.5 Report Generation

The agent generates a human-readable Markdown report:

`knowledge-cache/agent_outputs/issue_analysis/231.md`:

```markdown
# Issue Analysis: #231 - Auth service timeout

**Generated by:** issue-triage agent
**Date:** 2026-03-13T10:23:00Z
**Confidence:** 0.82

## Summary
Authentication timeout in OAuth flow affecting user login.

## Priority: HIGH
Affects user login flow with multiple user reports.

## Duplicates
- Possible duplicate of #198

## Related PRs
- #120 - OAuth token refresh changes
- #143 - Auth service timeout configuration

## Related Jira Tickets
- PROJ-89 - OAuth flow improvements

## Affected Components
- auth-service
- oauth-provider

## Suggested Actions
1. Investigate OAuth token refresh timeout
2. Check related PR #143 for regression

---
*Job ID: 12345 | Git Commit: abc123*
```

### 3.6 Ingestion API Endpoints

Add to API server:

```
POST /ingestion/github/sync     -> trigger GitHub sync (full or incremental)
GET  /ingestion/github/status   -> last sync status and stats
POST /ingestion/jira/sync       -> trigger Jira sync
GET  /ingestion/jira/status     -> last sync status and stats
```

### 3.7 Knowledge Browsing API

Implement the knowledge endpoints:

```
GET  /knowledge/issues                   -> list ingested issues
GET  /knowledge/issues/{number}          -> get specific issue data
GET  /knowledge/reports                  -> list generated reports
GET  /knowledge/reports/{type}/{id}      -> get specific report
GET  /knowledge/pull-requests            -> list ingested PRs
GET  /knowledge/jira-tickets             -> list ingested Jira tickets
```

## Deliverables

- [ ] GitHub fetcher ingests issues and PRs into knowledge cache
- [ ] Jira fetcher ingests tickets into knowledge cache
- [ ] Issue Triage Agent analyzes a GitHub issue using Gemini
- [ ] Structured JSON output produced with priority, duplicates, related items
- [ ] Markdown report generated and committed to knowledge cache
- [ ] LLM usage recorded (model, tokens, latency)
- [ ] Prompt and response stored for audit
- [ ] Event `issue.analyzed` published after completion
- [ ] Ingestion and knowledge browsing API endpoints working

## Definition of Done

You can:
1. Run `POST /ingestion/github/sync` to fetch issues from a real GitHub repo
2. Run `POST /jobs/run {"agent": "issue-triage", "parameters": {"issue_id": 231}}`
3. The agent fetches the issue, calls Gemini, generates a report
4. Report is committed to `knowledge-cache/agent_outputs/issue_analysis/231.md`
5. `GET /knowledge/reports/issue_analysis/231` returns the report
6. LLM usage is recorded in the database
7. An `issue.analyzed` event is in the events table
