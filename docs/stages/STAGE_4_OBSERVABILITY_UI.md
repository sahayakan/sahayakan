# Stage 4: Observability & UI

## Goal

Build real-time log streaming and the React + Material UI web dashboard. After this stage, users can watch agents execute live, browse reports, and manage jobs through a web interface.

## Dependencies

- Stage 3 completed (first agent pipeline working end-to-end)

## Tasks

### 4.1 Log Streaming Infrastructure

**Server-side (WebSocket):**

`control-plane/api-server/app/routes/websocket.py`:

```
WebSocket endpoint: /ws/logs/{job_id}
```

Flow:

```
Agent container writes to stdout
        |
        v
Runner captures log lines
        |
        v
Stores in memory buffer + writes to MinIO (archive)
        |
        v
WebSocket server broadcasts to connected clients
```

**Log message format (JSON over WebSocket):**

```json
{
  "timestamp": "2026-03-13T10:23:01Z",
  "job_id": "12345",
  "level": "INFO",
  "message": "Fetching GitHub issue #231",
  "stage": "collect_context"
}
```

**Log storage:**
- Live logs: in-memory buffer (last 1000 lines per job)
- Archived logs: stored in MinIO as `logs/{job_id}.jsonl`
- `logs_uri` field in `agent_runs` table points to MinIO URI

**API endpoints:**

```
GET  /logs/{job_id}          -> retrieve archived logs (paginated)
WS   /ws/logs/{job_id}      -> live log stream
```

### 4.2 React + Material UI Project Setup

`web-ui/`:

```
web-ui/
+-- public/
+-- src/
|   +-- App.jsx
|   +-- index.jsx
|   +-- theme.js
|   +-- api/
|   |   +-- client.js          # Axios/fetch wrapper
|   |   +-- agents.js
|   |   +-- jobs.js
|   |   +-- logs.js
|   |   +-- knowledge.js
|   +-- components/
|   |   +-- Layout/
|   |   |   +-- Sidebar.jsx
|   |   |   +-- Header.jsx
|   |   |   +-- MainLayout.jsx
|   |   +-- Jobs/
|   |   |   +-- JobList.jsx
|   |   |   +-- JobDetail.jsx
|   |   |   +-- JobRunButton.jsx
|   |   +-- Agents/
|   |   |   +-- AgentList.jsx
|   |   |   +-- AgentDetail.jsx
|   |   |   +-- ReviewGateConfig.jsx
|   |   +-- Logs/
|   |   |   +-- LogViewer.jsx
|   |   |   +-- LogLine.jsx
|   |   +-- Reports/
|   |   |   +-- ReportList.jsx
|   |   |   +-- ReportViewer.jsx
|   |   +-- Review/
|   |       +-- ReviewPanel.jsx
|   |       +-- ReviewDecisionDialog.jsx
|   +-- pages/
|   |   +-- DashboardPage.jsx
|   |   +-- JobsPage.jsx
|   |   +-- AgentsPage.jsx
|   |   +-- ReportsPage.jsx
|   |   +-- LogsPage.jsx
|   +-- hooks/
|       +-- useWebSocket.js
|       +-- useJobs.js
+-- package.json
+-- Dockerfile
```

**Tech stack:**
- React 18+
- Material UI (MUI) v5+
- React Router v6
- Axios for API calls
- Native WebSocket for log streaming

### 4.3 Dashboard Page

The main landing page showing system overview:

**Widgets:**

| Widget             | Content                              |
| ------------------ | ------------------------------------ |
| Active Jobs        | Count + list of currently running jobs |
| Recent Completions | Last 10 completed jobs with status   |
| Agent Status       | Registered agents and their health   |
| Pending Reviews    | Jobs awaiting human review           |
| Quick Actions      | Buttons to run agents, trigger sync  |

### 4.4 Jobs Page

**Job List View:**
- Table with columns: ID, Agent, Status, Created, Duration
- Filter by status (pending, running, completed, failed, awaiting_review)
- Sort by date
- Auto-refresh every 5 seconds

**Job Detail View:**
- Job metadata (agent, parameters, timestamps)
- Run status with stage indicator
- Embedded log viewer (live WebSocket stream)
- Artifacts list with download links
- Review panel (if job is awaiting review)
- LLM usage stats (model, tokens, cost)

### 4.5 Log Viewer Component

Real-time log viewer using WebSocket:

**Features:**
- Auto-scroll to bottom (toggleable)
- Color-coded log levels (INFO=default, LLM=blue, ERROR=red, GATE=yellow)
- Search/filter within logs
- Timestamp display
- Stage indicator (which lifecycle stage the agent is in)
- Copy log line
- Download full log

**WebSocket hook (`useWebSocket.js`):**

```javascript
function useWebSocket(jobId) {
  // Connect to /ws/logs/{jobId}
  // Buffer incoming messages
  // Handle reconnection
  // Return { logs, connected, error }
}
```

### 4.6 Report Viewer

Browse and view generated reports:

**Report List:**
- Filter by type (issue_analysis, pr_context, meeting_summary)
- Sort by date
- Search by content

**Report Detail:**
- Rendered Markdown report
- Raw JSON data view (toggle)
- Link to Git commit
- Link to source (issue, PR, or transcript)
- Metadata (agent, job, run, timestamps)

### 4.7 Review Panel

For jobs in `awaiting_review` status:

**Features:**
- Shows what stage the agent paused at
- Displays the current agent output/context at that stage
- Approve button (with optional comment)
- Reject button (with required reason)
- Review history for this job

**Review flow:**

```
Job paused at "after_analysis" stage
        |
        v
Review Panel shows:
  - Agent analysis results
  - Context used
  - Prompt sent
        |
        v
Reviewer clicks Approve or Reject
        |
        v
API call: POST /jobs/{id}/review
        |
        v
Agent resumes or job fails
```

### 4.8 Agents Page

**Agent List:**
- Registered agents with version, description
- Run count and success rate
- Last run timestamp

**Agent Detail:**
- Configuration
- Review gate settings (toggle per stage)
- Execution history
- LLM usage summary

### 4.9 Docker Configuration for Web UI

Add to `docker-compose.yml`:

```yaml
web-ui:
  build: ./web-ui
  ports:
    - "3000:3000"
  environment:
    - REACT_APP_API_URL=http://localhost:8000
  depends_on:
    - api-server
```

## Deliverables

- [ ] WebSocket log streaming from agent execution to browser
- [ ] Log archival in MinIO
- [ ] React + MUI project scaffolded and building
- [ ] Dashboard page with system overview widgets
- [ ] Jobs page with list/detail views
- [ ] Real-time log viewer with auto-scroll and color coding
- [ ] Report browser with Markdown rendering
- [ ] Review panel for approving/rejecting paused jobs
- [ ] Agents page with configuration and history
- [ ] Web UI containerized and added to Docker Compose

## Definition of Done

You can:
1. Open the dashboard at `http://localhost:3000`
2. See active and recent jobs
3. Click "Run Agent" and select issue-triage with an issue number
4. Watch the agent execute in real-time via the log viewer
5. View the generated report in the report browser
6. If a review gate is enabled, see the review panel and approve/reject
