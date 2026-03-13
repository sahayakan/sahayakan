# Stage 5: Remaining Agents & Event Bus

## Goal

Build the PR Context Agent, Meeting Summary Agent, and the event-driven agent orchestration system. After this stage, all three MVP agents are operational and can trigger each other through events.

## Dependencies

- Stage 4 completed (observability and UI working)

## Tasks

### 5.1 PR Context Agent

`data-plane/agents/pr-context/agent.py`:

**Purpose:** Analyzes pull requests to provide rich context for reviewers.

**load_input:**
- Receives `{"source": "github", "pr_number": 143}` or batch mode
- Loads PR JSON from knowledge cache

**collect_context:**
- Fetches PR diff summary from GitHub
- Searches knowledge cache for:
  - Linked issues (from PR body, commit messages)
  - Related Jira tickets
  - Previous analyses of related issues
  - Relevant Slack/meeting context (if available)

**analyze:**
- Sends structured prompt to Gemini with PR data + context

**generate_output:**

```json
{
  "status": "success",
  "pr_number": 143,
  "summary": "Fixes OAuth token refresh timeout by adding retry logic",
  "change_type": "bugfix",
  "risk_level": "medium",
  "risk_reasoning": "Modifies auth flow, needs careful testing",
  "linked_issues": [231, 198],
  "linked_jira_tickets": ["PROJ-89"],
  "components_modified": ["auth-service/oauth.py", "auth-service/token.py"],
  "test_coverage_notes": "Unit tests added for retry logic, integration test recommended",
  "review_suggestions": [
    "Verify timeout values against production SLAs",
    "Check if retry count is configurable"
  ],
  "breaking_changes": false,
  "confidence": 0.85
}
```

**Prompt template** (`data-plane/prompts/pr_context.prompt`):

```
You are an expert code reviewer analyzing a pull request.

## Pull Request
Title: {title}
Description: {body}
Changed files: {changed_files}
Diff summary: {diff_summary}

## Linked Issues
{linked_issues}

## Related Jira Tickets
{jira_tickets}

## Previous Related Analyses
{related_analyses}

## Instructions
Analyze this PR and provide a JSON response with:
- summary: concise description of the change
- change_type: "feature", "bugfix", "refactor", "docs", "test", "chore"
- risk_level: "low", "medium", "high", "critical"
- risk_reasoning: brief explanation
- linked_issues: list of issue numbers
- linked_jira_tickets: list of ticket keys
- components_modified: list of file paths
- test_coverage_notes: assessment of test coverage
- review_suggestions: list of things reviewer should check
- breaking_changes: true/false
- confidence: 0.0 to 1.0

Respond ONLY with valid JSON.
```

**Report output:** `knowledge-cache/agent_outputs/pr_context/{pr_number}.md`

### 5.2 Meeting Summary Agent

`data-plane/agents/meeting-summary/agent.py`:

**Purpose:** Extracts structured information from meeting transcripts.

**load_input:**
- Receives `{"source": "meeting", "transcript_id": "2026-03-13-standup"}`
- Loads transcript from `knowledge-cache/meetings/transcripts/`

**Input format for transcripts:**

Transcripts can be uploaded via API or placed in the knowledge cache:

```
knowledge-cache/meetings/transcripts/2026-03-13-standup.txt
```

Format:

```
Meeting: Daily Standup
Date: 2026-03-13
Attendees: Alice, Bob, Carol

[00:00] Alice: Let's start with updates...
[00:45] Bob: I've been working on the auth timeout issue...
[02:30] Carol: The Jira board needs cleanup...
```

**collect_context:**
- Searches for mentioned issues, PRs, Jira tickets in the transcript
- Loads related data from knowledge cache

**analyze:**
- Sends transcript + context to Gemini

**generate_output:**

```json
{
  "status": "success",
  "meeting_id": "2026-03-13-standup",
  "title": "Daily Standup - 2026-03-13",
  "attendees": ["Alice", "Bob", "Carol"],
  "summary": "Team discussed auth timeout issue, Jira cleanup, and sprint planning",
  "action_items": [
    {
      "assignee": "Bob",
      "action": "Investigate OAuth token refresh timeout",
      "related_issue": 231,
      "due": "2026-03-15"
    },
    {
      "assignee": "Carol",
      "action": "Clean up Jira backlog",
      "related_jira": "PROJ-90",
      "due": "2026-03-14"
    }
  ],
  "decisions": [
    "Move auth timeout fix to P1",
    "Schedule architecture review for next week"
  ],
  "mentioned_issues": [231, 198],
  "mentioned_prs": [143],
  "mentioned_jira_tickets": ["PROJ-89", "PROJ-90"],
  "key_topics": ["auth-service", "sprint-planning", "jira-cleanup"],
  "confidence": 0.78
}
```

**Prompt template** (`data-plane/prompts/meeting_summary.prompt`):

```
You are an expert at summarizing engineering meetings.

## Transcript
{transcript}

## Related Context
Issues mentioned: {related_issues}
PRs mentioned: {related_prs}
Jira tickets mentioned: {jira_tickets}

## Instructions
Analyze this meeting transcript and provide a JSON response with:
- title: meeting title
- attendees: list of attendee names
- summary: 2-3 sentence overview
- action_items: list of {assignee, action, related_issue/jira, due}
- decisions: list of decisions made
- mentioned_issues: list of GitHub issue numbers
- mentioned_prs: list of PR numbers
- mentioned_jira_tickets: list of Jira ticket keys
- key_topics: list of main topics discussed
- confidence: 0.0 to 1.0

Respond ONLY with valid JSON.
```

**Report output:** `knowledge-cache/agent_outputs/meeting_summaries/{meeting_id}.md`

**API for transcript upload:**

```
POST /knowledge/meetings/transcripts    -> upload a meeting transcript
GET  /knowledge/meetings/transcripts    -> list uploaded transcripts
```

### 5.3 Event Bus Implementation

`control-plane/event-bus/processor.py`:

The event bus connects agents together. It polls the `events` table and triggers subscribed agents.

**Event types:**

| Event                    | Published by       | Triggers             |
| ------------------------ | ------------------ | -------------------- |
| `issue.ingested`         | GitHub fetcher     | issue-triage agent   |
| `issue.analyzed`         | Issue Triage Agent | pr-context agent (if related PRs found) |
| `pr.ingested`            | GitHub fetcher     | pr-context agent     |
| `pr.analyzed`            | PR Context Agent   | (future agents)      |
| `meeting.uploaded`       | API/manual         | meeting-summary agent |
| `meeting.summarized`     | Meeting Summary    | (future agents)      |
| `jira.ingested`          | Jira fetcher       | (enrichment)         |

**Event processor loop:**

```python
while running:
    events = fetch_unprocessed_events()
    for event in events:
        subscriptions = get_subscriptions(event.event_type)
        for sub in subscriptions:
            create_job(
                agent_name=sub.agent_name,
                parameters=event.payload
            )
        mark_event_processed(event.id)
    sleep(poll_interval)
```

**Event publishing (from agents):**

```python
def publish_event(event_type: str, source: str, payload: dict):
    insert_event(event_type, source, payload)
    # Also commit event record to knowledge cache for audit
    write_event_to_git(event_type, source, payload)
```

**Event audit trail:**

Events are also committed to Git:

```
knowledge-cache/events/
    2026-03-13/
        issue-analyzed-231.json
        pr-analyzed-143.json
        meeting-summarized-2026-03-13-standup.json
```

### 5.4 Agent Subscription Registration

Default subscriptions for MVP:

```python
# Issue Triage subscribes to new issues
register_subscription("issue-triage", "issue.ingested")

# PR Context subscribes to new PRs and analyzed issues (for cross-referencing)
register_subscription("pr-context", "pr.ingested")
register_subscription("pr-context", "issue.analyzed")

# Meeting Summary subscribes to uploaded transcripts
register_subscription("meeting-summary", "meeting.uploaded")
```

### 5.5 API Endpoints for Events

```
GET  /events                          -> list events (paginated, filterable)
GET  /events/{id}                     -> get event details
GET  /events/types                    -> list all event types
POST /events/publish                  -> manually publish an event (for testing)
GET  /agents/{name}/subscriptions     -> list agent's subscriptions
POST /agents/{name}/subscriptions     -> add subscription
DELETE /agents/{name}/subscriptions/{event_type} -> remove subscription
```

### 5.6 UI Updates

**Dashboard additions:**
- Event stream widget (recent events with type and source)
- Agent pipeline visualization (which agent triggered which)

**New pages/components:**
- Events page: list/filter events, view event chains
- Agent pipeline view: visual flow of event-triggered executions

**Reports page updates:**
- Add PR context reports
- Add meeting summary reports
- Filter by report type

## Deliverables

- [ ] PR Context Agent analyzes pull requests with Gemini
- [ ] Meeting Summary Agent processes transcripts with Gemini
- [ ] Meeting transcript upload API working
- [ ] Event bus processor polls and triggers subscribed agents
- [ ] Default subscriptions registered for all three agents
- [ ] Events committed to knowledge cache for audit
- [ ] Agent chains work: issue ingested -> triage -> PR context triggered
- [ ] Event management API endpoints
- [ ] UI updated with event stream and new report types
- [ ] All three agents produce Markdown reports in knowledge cache

## Definition of Done

You can:
1. Trigger a GitHub sync that ingests issues
2. Event `issue.ingested` fires and triggers the Issue Triage Agent
3. Issue Triage Agent completes and publishes `issue.analyzed`
4. If related PRs exist, PR Context Agent is triggered automatically
5. Upload a meeting transcript and have it analyzed automatically
6. View the full event chain in the UI
7. Browse all three types of reports in the report viewer
