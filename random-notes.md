# Agentic AI Development System

## MVP Technical Specification

## 1. Objective

Build a **minimal but functional AI agent platform** that assists software teams by analyzing development data and producing traceable reports.

The MVP will:

* ingest development data
* allow agents to run jobs
* store outputs and metadata
* stream execution logs to users
* maintain **full traceability through Git**

The system will initially support agents that analyze:

* GitHub issues
* Pull requests
* meeting transcripts

---

# 2. High-Level Architecture

```
                External Systems
          ┌──────────┬───────────┬─────────────┐
          ▼          ▼           ▼
        GitHub      Jira        Slack
          │           │           │
          └───── Data Ingestion ──┘
                     │
                     ▼
            Knowledge Cache (Git)
                     │
                     ▼
             Agent Runtime System
                     │
        ┌────────────┼─────────────┐
        ▼            ▼             ▼
    PostgreSQL    Blob Storage   Logs
     Metadata        MinIO      Streaming
                     │
                     ▼
                Web Dashboard
```

---

# 3. Core Components

The MVP will consist of **six primary subsystems**.

| Component       | Purpose                |
| --------------- | ---------------------- |
| Agent Runtime   | Executes agents        |
| Knowledge Cache | Local data aggregation |
| Metadata Store  | Tracks agent runs      |
| Blob Storage    | Stores artifacts       |
| API Server      | System entrypoint      |
| Web Dashboard   | UI for users           |

---

# 4. Infrastructure Stack

Recommended stack for the MVP:

| Layer           | Technology     |
| --------------- | -------------- |
| Runtime         | Docker         |
| Agent language  | Python         |
| API server      | FastAPI        |
| Metadata DB     | PostgreSQL     |
| Blob storage    | MinIO          |
| Knowledge store | Git repository |
| Frontend        | React          |
| Log streaming   | WebSocket      |
| Deployment      | Linux VM       |

---

# 5. Directory Layout

Example system layout:

```
agent-platform/
│
├── api-server/
├── agents/
│   ├── issue-triage-agent
│   ├── pr-context-agent
│   └── meeting-summary-agent
│
├── knowledge-cache/
│
├── infrastructure/
│   ├── docker-compose.yml
│   └── configs
│
└── web-ui/
```

---

# 6. Knowledge Cache

The system maintains a **local Git repository** containing project knowledge.

```
knowledge-cache/

github/
   issues/
   pull_requests/

jira/
   tickets/

slack/
   thread_summaries/

meetings/
   transcripts/

agent_outputs/
   issue_analysis/
   pr_context/
```

Agents read from and write to this repository.

Benefits:

* version control
* human readable
* auditability
* rollback capability

---

# 7. Metadata Storage (PostgreSQL)

PostgreSQL will store **structured system data**.

## Tables

### agents

```
id
name
description
version
created_at
```

---

### agent_runs

Tracks every execution.

```
id
agent_id
status
input_source
start_time
end_time
log_stream_id
result_commit
```

---

### artifacts

```
id
run_id
type
storage_uri
created_at
```

---

### jobs

Tracks queued executions.

```
id
agent_name
status
created_at
started_at
completed_at
parameters
```

---

# 8. Blob Storage

Large files are stored in **MinIO object storage**.

Examples:

```
blobs/

meeting-audio/
embeddings/
datasets/
large-transcripts/
execution-artifacts/
```

Metadata stored in PostgreSQL references these files.

Example:

```
artifact
storage_uri = s3://agent-platform/blobs/meeting-audio/123.mp3
```

---

# 9. Agent Runtime

Agents run inside **Docker containers**.

Each agent follows a common structure.

```
agent/

agent.py
config.yaml
Dockerfile
requirements.txt
```

---

## Agent Interface

All agents must implement:

```
run(input)
generate_report()
store_results()
```

Example flow:

```
agent start
     │
fetch data
     │
analyze
     │
generate report
     │
commit to knowledge cache
     │
update metadata DB
```

---

# 10. Job Execution Model

Agents run as **jobs**.

Example:

```
POST /jobs/run
```

Payload:

```
{
  "agent": "issue-triage",
  "issue_id": 123
}
```

Execution flow:

```
API Server
   │
create job
   │
Job Queue
   │
Agent Runner
   │
Agent Container
```

---

# 11. Log Streaming

Logs are streamed to the UI.

Architecture:

```
Agent container
      │
stdout logs
      │
log streamer
      │
WebSocket server
      │
web dashboard
```

Users see live execution logs.

Example:

```
Fetching issue #231
Searching related PRs
Running LLM analysis
Generating report
Committing result
Completed
```

---

# 12. API Server

API server provides system access.

Endpoints:

### Agent management

```
GET /agents
GET /agents/{id}
```

---

### Job control

```
POST /jobs/run
GET /jobs/{id}
GET /jobs
```

---

### Logs

```
GET /logs/{job_id}
```

WebSocket endpoint:

```
/ws/logs/{job_id}
```

---

### Knowledge browsing

```
GET /knowledge/issues
GET /knowledge/reports
```

---

# 13. Web Dashboard

UI for developers and managers.

Features:

### Agent monitoring

```
Active jobs
Agent status
Execution history
```

---

### Log viewer

Real-time agent execution.

---

### Knowledge explorer

Browse generated reports.

---

### Insights dashboard

Future feature.

---

# 14. Data Ingestion

A scheduled process syncs external data into the knowledge cache.

Example schedule:

```
GitHub issues sync → every 10 minutes
Jira sync → every 30 minutes
Slack summaries → hourly
Meeting transcripts → manual upload
```

This reduces dependency on live APIs.

---

# 15. Security

Basic authentication for MVP.

Options:

```
API keys
GitHub OAuth
```

Secrets stored in environment variables.

---

# 16. Deployment

Single-node deployment.

```
Linux VM
│
Docker
│
docker-compose
```

Services:

```
postgres
minio
api-server
agent-runner
web-ui
```

---

# 17. Initial Agents (MVP)

### Issue Triage Agent

Input:

```
GitHub issue
```

Output:

```
priority suggestion
duplicate detection
related PRs
```

Stored as:

```
knowledge-cache/agent_outputs/issue_analysis/
```

---

### PR Context Agent

Input:

```
pull request
```

Output:

```
summary
linked Jira tickets
relevant discussions
```

---

### Meeting Summary Agent

Input:

```
meeting transcript
```

Output:

```
action items
decisions
linked tasks
```

---

# 18. Traceability Model

Every agent run produces:

1. **Git commit**
2. **database record**
3. **artifact reference**

Example commit:

```
[AI-Agent] Issue Analysis

Agent: issue-triage
Source: GitHub Issue #231
Run: 2026-03-13T10:23
```

---

# 19. MVP Success Criteria

The MVP is successful if it can:

* ingest GitHub issues
* run an agent analysis
* store outputs in Git
* track execution metadata
* stream logs to users

---

# 20. Estimated Complexity

A small team could build this MVP in roughly:

```
4–6 weeks
```

Core effort:

| Component           | Difficulty |
| ------------------- | ---------- |
| Agent runtime       | medium     |
| API server          | medium     |
| Git knowledge cache | easy       |
| PostgreSQL schema   | easy       |
| Web UI              | medium     |
| Log streaming       | medium     |

---

✅ This MVP would already demonstrate **real value** and align well with your goals of:

* data-driven decisions
* human-in-the-loop oversight
* full traceability

# 1. Architecture

Instead of supporting multiple model providers, the system will use **Vertex AI as the single LLM backend**.

```text
             External Systems
        ┌──────────┬───────────┬─────────────┐
        ▼          ▼           ▼
      GitHub      Jira        Slack
        │           │           │
        └──── Data Ingestion ───┘
                   │
                   ▼
          Knowledge Cache (Git)
                   │
                   ▼
              Agent Runtime
                   │
                   ▼
        Vertex AI Gemini API
                   │
        ┌──────────┼──────────┐
        ▼          ▼          ▼
    PostgreSQL    MinIO     Logs
      metadata     blobs   streaming
```

So the **LLM layer becomes external infrastructure**.

---

# 2. Why Vertex AI Is Good for This MVP

Advantages:

### No GPU infrastructure

You avoid:

```
model servers
GPU nodes
model deployment
model updates
```

Everything is managed by Google.

---

### Multimodal support

Gemini can process:

```
text
images
audio
documents
```

Useful later for:

```
meeting recordings
screenshots
design documents
```

---

### Large context window

Gemini models support **very large contexts**, which helps agents analyze:

```
multiple issues
long Slack threads
meeting transcripts
PR discussions
```

---

# 3. Agent → Gemini Interaction Model

Agents call Gemini through the **Vertex AI API**.

Example flow:

```text
Agent runtime
     │
     │ request
     ▼
Gemini API
     │
     │ response
     ▼
Agent continues processing
```

---

# 4. Standard LLM Interface Layer

Even though you use only Gemini, **create an abstraction layer**.

Example:

```python
class LLMClient:
    def generate(self, prompt):
        pass
```

Gemini implementation:

```python
class GeminiClient(LLMClient):
    def generate(self, prompt):
        # Vertex AI call
```

Why this matters:

Future flexibility.

You could later add:

```
OpenAI
Claude
local models
```

Without rewriting agents.

---

# 5. Vertex AI Authentication

Use **Google service accounts**.

Environment setup:

```
GOOGLE_APPLICATION_CREDENTIALS=/secrets/service-account.json
```

Agents authenticate automatically.

---

# 6. Example Gemini API Call (Python)

Example using Vertex AI SDK:

```python
from vertexai.generative_models import GenerativeModel

model = GenerativeModel("gemini-1.5-pro")

response = model.generate_content(
    "Summarize this GitHub issue and suggest priority."
)

print(response.text)
```

Agents will send:

```
issue text
PR diff
Slack messages
meeting transcripts
```

---

# 7. Prompt Templates

Store prompt templates in the repository.

Example:

```text
prompts/

issue_analysis.prompt
pr_context.prompt
meeting_summary.prompt
```

Example template:

```
You are an engineering assistant.

Analyze the following GitHub issue and determine:

1. Priority
2. Possible duplicates
3. Related components
4. Suggested next actions
```

This keeps prompts **version-controlled**.

---

# 8. Handling Large Context Inputs

Many analyses will involve large text.

Use this strategy:

```
Agent
   │
chunk documents
   │
combine summaries
   │
final synthesis prompt
```

Gemini large context reduces the need for complex chunking.

---

# 9. Gemini Cost Control

To avoid cost surprises:

Store token usage metadata.

Example table:

```
llm_usage

id
agent_run_id
model
tokens_input
tokens_output
estimated_cost
timestamp
```

This lets you build a **cost dashboard later**.

---

# 10. Failure Handling

LLM APIs fail sometimes.

Agents must handle:

```
rate limits
timeouts
network errors
partial responses
```

Example retry policy:

```
max retries: 3
exponential backoff
```

---

# 11. Data Privacy Considerations

Since Gemini is external:

Sensitive internal data is sent to Google.

Mitigation:

```
strip secrets
remove credentials
sanitize logs
```

Agents should sanitize input.

---

# 12. Logging LLM Interactions

For traceability store:

```
prompt
model
parameters
response
```

Example artifact:

```
knowledge-cache/agent_outputs/llm_calls/
```

This helps debugging.

---

# 13. Updated Agent Workflow

Example:

Issue triage agent.

```
fetch GitHub issue
      │
collect related context
      │
build prompt
      │
call Gemini
      │
process response
      │
generate report
      │
commit report to Git
      │
record metadata
```

---

# 14. Recommended Gemini Models

For MVP:

| Task       | Model            |
| ---------- | ---------------- |
| analysis   | Gemini 1.5 Pro   |
| fast tasks | Gemini 1.5 Flash |

Strategy:

```
analysis → Pro
short summaries → Flash
```

---

# 15. MVP Infrastructure (Final)

Your simplified stack becomes:

```
Linux VM
Docker
FastAPI
PostgreSQL
MinIO
React UI
Vertex AI Gemini API
Git knowledge cache
```

This is a **clean, realistic MVP stack**.

---

# 16. Estimated Operational Cost

Very rough monthly estimate (small team usage):

```
LLM usage
$50–$300

VM
$20–$40

Storage
$10
```

So the entire system might run for **under $400/month**.

---

✅ **Conclusion**

Using **Gemini via Vertex AI is an excellent MVP decision** because it:

* eliminates ML infrastructure
* supports large contexts
* supports multimodal data
* scales easily
* reduces operational complexity

# Agent Execution Contract (MVP Specification)

## 1. Purpose

The **Agent Execution Contract** defines:

* how agents are started
* how inputs are provided
* how outputs are produced
* how logs are streamed
* how results are stored

Every agent in the system must follow this contract.

This ensures:

* predictable execution
* easier debugging
* easy addition of new agents
* traceability

---

# 2. Agent Lifecycle

Every agent run follows the same lifecycle.

```
Job Created
     │
     ▼
Agent Started
     │
     ▼
Data Collection
     │
     ▼
Analysis (LLM)
     │
     ▼
Result Generation
     │
     ▼
Artifact Storage
     │
     ▼
Completion
```

Each stage should produce **log messages**.

---

# 3. Agent Execution Environment

Each agent runs inside a **Docker container**.

Example container:

```
agent-issue-triage
```

Environment variables provided:

```
JOB_ID
AGENT_NAME
INPUT_SOURCE
KNOWLEDGE_REPO_PATH
POSTGRES_URI
MINIO_ENDPOINT
VERTEX_PROJECT
VERTEX_LOCATION
```

This makes agents **stateless and portable**.

---

# 4. Standard Agent Interface

Every agent must implement this interface.

Example (Python):

```python
class Agent:

    def load_input(self):
        pass

    def collect_context(self):
        pass

    def analyze(self):
        pass

    def generate_output(self):
        pass

    def store_artifacts(self):
        pass
```

Execution order:

```
load_input
collect_context
analyze
generate_output
store_artifacts
```

---

# 5. Standard Input Format

All agents receive a **JSON input payload**.

Example:

```json
{
  "job_id": "12345",
  "agent": "issue-triage",
  "input": {
    "source": "github",
    "issue_id": 231
  },
  "parameters": {
    "analysis_depth": "normal"
  }
}
```

This payload is passed via:

```
stdin
```

or

```
input.json file
```

---

# 6. Agent Output Format

Agents must return a **structured JSON result**.

Example:

```json
{
  "status": "success",
  "summary": "Possible duplicate of issue #198",
  "priority": "medium",
  "related_prs": [120, 143],
  "confidence": 0.78
}
```

This JSON is stored in:

```
knowledge-cache/agent_outputs/
```

---

# 7. Artifact Model

Agents may produce artifacts.

Examples:

* reports
* transcripts
* embeddings
* LLM prompts
* analysis results

Artifacts must follow this structure:

```
artifact/
    run_id
    artifact_type
    storage_uri
```

Example:

```
artifact_type: issue-analysis-report
storage_uri: knowledge-cache/issue_analysis/231.md
```

---

# 8. Logging Contract

Agents must log progress using structured logs.

Example:

```
[INFO] Starting issue analysis
[INFO] Fetching GitHub issue #231
[INFO] Fetching related PRs
[INFO] Calling Gemini API
[INFO] Generating report
[INFO] Committing results
```

Logs must be written to:

```
stdout
```

The runtime streams these logs to users.

---

# 9. LLM Interaction Rules

All agents must use the **shared LLM client** for Gemini.

Example:

```python
response = llm.generate(prompt)
```

Agents must log:

```
model used
token count
response time
```

Example:

```
[LLM] model=gemini-1.5-pro tokens=1200 latency=2.3s
```

---

# 10. Error Handling

Agents must return structured errors.

Example:

```json
{
  "status": "error",
  "error_type": "llm_timeout",
  "message": "Vertex AI request timed out"
}
```

Retry policy handled by runtime.

---

# 11. Git Traceability

Every agent run must create a **Git commit**.

Example:

```
[AI-Agent] Issue Analysis

Agent: issue-triage
Job ID: 12345
Source: GitHub Issue #231
Timestamp: 2026-03-13
```

Files committed:

```
knowledge-cache/agent_outputs/issue_analysis/231.md
```

This creates **complete auditability**.

---

# 12. Metadata Recording

After execution the runtime records metadata.

Example:

```
agent_runs
```

Fields:

```
run_id
agent_name
status
start_time
end_time
artifact_count
llm_tokens_used
git_commit
```

Stored in PostgreSQL.

---

# 13. Agent Resource Limits

Each agent should have limits.

Example:

```
max runtime: 10 minutes
max memory: 1 GB
max LLM calls: 10
```

Configured in Docker.

---

# 14. Deterministic Output Requirement

Agents should aim for **repeatable outputs**.

Strategies:

```
low temperature
structured prompts
strict JSON output
```

This improves reliability.

---

# 15. Agent Registration

Agents must register with the platform.

Example:

```
POST /agents/register
```

Payload:

```json
{
  "name": "issue-triage",
  "version": "1.0",
  "description": "Analyzes GitHub issues"
}
```

This allows the system to discover available agents.

---

# 16. Minimal Agent Example

Example structure:

```
issue-triage-agent/
   agent.py
   prompts/
   Dockerfile
```

Main script:

```python
def main():
    agent = IssueTriageAgent()
    agent.run()
```

---

# 17. Agent Execution Example

A full run looks like this.

```
Job created
   │
Agent container starts
   │
Input loaded
   │
GitHub issue fetched
   │
Gemini analysis
   │
Report generated
   │
Report committed to Git
   │
Metadata stored
   │
Job completed
```

---

# 18. Why This Contract Matters

Without a contract:

```
agents behave differently
logs inconsistent
results unpredictable
```

With a contract:

```
plug-and-play agents
predictable execution
easy debugging
consistent data
```

# 1. What Is an Agent Bus?

An **Agent Bus** is an **event system that connects agents together**.

Instead of manually triggering agents, they react to **events**.

Example:

```text
Issue Created
      │
      ▼
Issue Triage Agent
      │
      ▼
Priority Assigned
      │
      ▼
PR Context Agent
```

Agents publish events → other agents subscribe.

---

# 2. Why You Want This

Without an event system:

```text
User
   │
   ▼
Run Agent A
   │
   ▼
Run Agent B
```

Everything is manual.

With an agent bus:

```text
Agent A finished
      │
      ▼
Event published
      │
      ▼
Agent B triggered automatically
```

The system becomes **autonomous but traceable**.

---

# 3. Example Workflow

Example development workflow.

```text
GitHub Issue Created
      │
      ▼
Event: issue.created
      │
      ▼
Issue Triage Agent
      │
      ▼
Event: issue.analyzed
      │
      ▼
Planning Agent
```

Each step generates **structured events**.

---

# 4. Basic Agent Bus Architecture

For the MVP the architecture can be simple.

```text
          Agents
            │
            ▼
        Event Bus
            │
            ▼
       Agent Scheduler
```

Components:

* event publisher
* event queue
* event subscribers

---

# 5. Event Structure

Events must have a standard format.

Example:

```json
{
  "event_id": "evt-123",
  "type": "issue.analyzed",
  "timestamp": "2026-03-13T10:12:00Z",
  "source_agent": "issue-triage",
  "data": {
    "issue_id": 231,
    "priority": "high"
  }
}
```

Events should also be stored in **PostgreSQL**.

Table example:

```text
events
------
event_id
event_type
source_agent
payload
timestamp
```

---

# 6. How Agents Use the Bus

Agents can do two things.

### Publish events

Example:

```text
Issue triage completed
```

Agent publishes:

```text
issue.analyzed
```

---

### Subscribe to events

Example:

```text
Planning agent subscribes to:

issue.analyzed
```

When event appears → agent runs.

---

# 7. Minimal MVP Event Bus

You do **not need heavy infrastructure** initially.

The simplest bus:

```text
PostgreSQL event table
```

Workflow:

```
Agent publishes event
      │
      ▼
Insert row in events table
      │
      ▼
Scheduler polls events
      │
      ▼
Trigger subscribed agents
```

This is simple and reliable.

---

# 8. Later Upgrade Options

If system grows you can introduce real event streaming.

Examples:

* Apache Kafka
* NATS
* Redis Streams

But **not necessary for MVP**.

---

# 9. Example Event Flow

Let's walk through a real scenario.

### Step 1

GitHub issue ingested.

Event:

```text
issue.created
```

---

### Step 2

Issue triage agent runs.

Produces:

```text
issue.analyzed
```

---

### Step 3

PR context agent subscribes.

Triggered automatically.

Produces:

```text
pr.context.generated
```

---

### Step 4

Report generator agent runs.

Produces:

```text
report.created
```

---

The system becomes a **pipeline of intelligent agents**.

---

# 10. Visual Architecture

```text
             Event Bus
                │
 ┌──────────────┼──────────────┐
 ▼              ▼              ▼
Issue Agent   PR Agent    Meeting Agent
    │              │              │
    └────── publish events ───────┘
```

---

# 11. Why This Is Powerful

The Agent Bus allows:

### automation

Agents trigger other agents.

---

### modularity

Agents remain independent.

---

### traceability

Events show **why something happened**.

---

### scalability

Adding a new agent is easy.

Example:

```
subscribe to: issue.analyzed
```

Done.

---

# 12. Example Event Table

Example PostgreSQL table:

```sql
CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    event_type TEXT,
    source_agent TEXT,
    payload JSONB,
    created_at TIMESTAMP
);
```

Simple and effective.

---

# 13. Event Logging for Audit

Every event should also be committed to Git.

Example:

```text
knowledge-cache/events/
   2026-03-13/
      issue-analyzed-231.json
```

This keeps **historical traceability**.

---

# 14. Relationship to Your Philosophy

Your framework emphasized:

* traceability
* human oversight
* data-driven decisions

The Agent Bus supports this perfectly.

Events show:

```text
what triggered the agent
why it ran
what data it produced
```

---

# 15. What the MVP Should Include

For MVP:

Implement:

```text
event table (Postgres)
event publisher
event subscriber
simple scheduler
```

Skip:

```text
Kafka
distributed streaming
complex orchestration
```

---

# 16. Future Possibilities

Once you have the bus, you can build:

* autonomous engineering assistants
* automated project analytics
* continuous code review
* intelligent backlog prioritization

All built as **small independent agents**.

---

✅ **Important insight**

Your architecture is actually very similar to:

* CI pipelines
* data engineering pipelines
* distributed microservices

# 1. The Three Memory Layers

Your agent platform should have:

```
Agent Memory System
     │
     ├── Working Memory
     ├── Knowledge Memory
     └── Long-Term Memory
```

Each serves a different purpose.

---

# 2. Working Memory (Short-Term)

This is **temporary memory for the current job execution**.

Example:

```
Agent run:
  issue #231 analysis
```

The agent collects:

```
issue text
related PRs
Slack thread
Jira ticket
```

All of this becomes **working context** for the LLM call.

Example:

```
working_context/
   issue_231.json
   related_prs.json
   slack_summary.txt
```

Characteristics:

| property | value              |
| -------- | ------------------ |
| lifetime | single job         |
| storage  | local filesystem   |
| purpose  | LLM prompt context |

After the job finishes, it can be discarded.

---

# 3. Knowledge Memory (Project Knowledge)

This is the **shared project knowledge base**.

In your architecture, this is exactly the **Git knowledge cache**.

Example structure:

```
knowledge-cache/

github/
   issues/
   pull_requests/

slack/
   summaries/

meetings/
   transcripts/

agent_outputs/
   issue_analysis/
```

Properties:

| property | value                    |
| -------- | ------------------------ |
| lifetime | persistent               |
| storage  | Git repository           |
| purpose  | shared project knowledge |

This memory allows agents to reason about **historical project data**.

Example usage:

```
Agent analyzing issue
   ↓
search previous issues
   ↓
detect duplicate
```

---

# 4. Long-Term Memory (Insights)

This layer stores **derived insights and patterns**.

Examples:

```
recurring bug patterns
technical debt signals
slow PR areas
frequent regressions
```

Example table:

```
insights
---------
id
type
description
evidence
created_at
confidence
```

Stored in **PostgreSQL**.

Example insight:

```
Type: recurring_bug
Component: auth_service
Evidence: issues #120, #145, #212
Confidence: 0.81
```

Agents can consult this memory before making decisions.

---

# 5. Where Each Memory Lives

```
Agent Platform Storage

Working Memory
    │
    └─ container filesystem

Knowledge Memory
    │
    └─ Git repository

Long-Term Memory
    │
    └─ PostgreSQL
```

Optional later:

```
semantic memory
   ↓
vector database
```

---

# 6. Memory Flow During an Agent Run

Example workflow.

```
Agent starts
      │
      ▼
Load knowledge memory
      │
      ▼
Build working memory
      │
      ▼
Call Gemini
      │
      ▼
Produce result
      │
      ▼
Update knowledge memory
      │
      ▼
Store insights
```

So memory is **both input and output**.

---

# 7. Example: Issue Analysis Agent

### Step 1

Fetch issue.

Working memory:

```
issue_231.json
```

---

### Step 2

Load related context.

From knowledge memory:

```
previous issue summaries
PR history
Slack summaries
```

---

### Step 3

Gemini analysis.

Prompt contains:

```
working memory
+
knowledge memory
```

---

### Step 4

Output.

Stored in knowledge memory:

```
knowledge-cache/issue_analysis/231.md
```

---

### Step 5

Derived insight stored.

Example:

```
pattern: duplicate issues in auth module
```

Stored in PostgreSQL.

---

# 8. Optional Layer Later: Semantic Memory

When the knowledge base grows large, add a **vector index**.

Example vector DB options:

* Qdrant
* Weaviate
* pgvector

This allows queries like:

```
find similar issues
find related Slack discussions
```

But for MVP you can skip it.

---

# 9. Memory Governance

Because agents write knowledge, governance is important.

Policies:

### Agent output review

Major insights may require human approval.

---

### Git history

All knowledge changes are versioned.

---

### Confidence tracking

Insights include confidence scores.

---

# 10. Why This Design Works Well

This architecture balances:

| Requirement        | Solution           |
| ------------------ | ------------------ |
| traceability       | Git knowledge base |
| structured queries | PostgreSQL         |
| temporary context  | working memory     |
| future scalability | vector memory      |

It also keeps the system **very understandable to engineers**.

---

# 11. How This Fits Your Philosophy

Your system emphasizes:

* data-driven development
* traceability
* human oversight

The memory layers enable:

```
AI reasoning
+
human inspectability
```

Because everything important is stored in **Git or PostgreSQL**.

---

# 12. Final Architecture With Memory

```
                Agents
                   │
                   ▼
            Working Memory
                   │
                   ▼
            Knowledge Memory
                (Git)
                   │
                   ▼
            Long-Term Memory
              (PostgreSQL)
```

Optional later:

```
Semantic Memory
(vector database)
```

Below are the **10 biggest mistakes**, along with how your current design avoids or should address them.

---

# 1. No Traceability of Agent Actions

### The mistake

Agents produce results but no one knows:

* what data was used
* what prompt was sent
* what model responded
* why the decision was made

This leads to **untrustworthy systems**.

### Correct approach

Your design already solves this by storing:

* prompts
* responses
* Git commits
* metadata

This creates a **complete audit trail**.

Example record:

```text
Agent: issue-triage
Input: GitHub issue #231
Model: Gemini 1.5 Pro
Prompt hash: 84adf2
Output commit: 1f92c3
```

This is excellent practice.

---

# 2. Agents Without Clear Contracts

### The mistake

Each agent behaves differently:

```text
Agent A outputs JSON
Agent B outputs Markdown
Agent C outputs nothing
```

This makes orchestration impossible.

### Correct approach

Your **Agent Execution Contract** solves this.

All agents must follow:

* standard input
* standard output
* standard lifecycle
* structured logs

---

# 3. Mixing All Data Into One Storage System

### The mistake

Many systems try to store everything in one place:

* database
* vector store
* file system

This causes:

* performance problems
* complexity
* poor maintainability

### Correct approach

Your architecture separates storage:

```text
PostgreSQL  → metadata
Git repo    → knowledge
MinIO       → blobs
```

This is the **right pattern**.

---

# 4. Overusing Vector Databases Too Early

### The mistake

People immediately add:

* embeddings
* semantic search
* vector DB

Even when the dataset is small.

This adds unnecessary complexity.

### Correct approach

Your MVP wisely avoids this.

You can add vector search later when the knowledge base grows.

---

# 5. Agents That Are Too Autonomous

### The mistake

People design agents that:

* make decisions
* modify systems
* deploy code

without human oversight.

This is dangerous.

### Correct approach

Your system enforces **human-in-the-loop governance**.

Agents provide:

```text
suggestions
analysis
summaries
insights
```

Humans approve actions.

---

# 6. No Event Architecture

### The mistake

Agents are triggered manually.

This limits automation.

Example:

```text
user runs agent A
user runs agent B
```

### Correct approach

Your **Agent Bus** solves this.

Agents react to events.

Example:

```text
issue.created
    ↓
issue.analyzed
    ↓
report.generated
```

This allows scalable workflows.

---

# 7. No Observability

### The mistake

Agents run silently.

Users cannot see:

* what the agent is doing
* whether it's stuck
* what step failed

### Correct approach

Your system includes:

* real-time log streaming
* execution history
* metadata tracking

Users can watch agent progress live.

---

# 8. Tightly Coupled Agents

### The mistake

Agents directly call other agents.

Example:

```text
issue agent → pr agent → meeting agent
```

This creates fragile systems.

### Correct approach

Use **events instead of direct calls**.

Agents publish events.

Other agents subscribe.

Loose coupling improves scalability.

---

# 9. Ignoring Cost Monitoring

### The mistake

LLM usage grows uncontrollably.

People forget to track:

* token usage
* model costs
* prompt size

Costs can explode.

### Correct approach

Your design stores:

```text
model used
token counts
latency
cost estimate
```

This enables cost dashboards.

Since you're using **Gemini on Vertex AI**, this is important.

---

# 10. No Deterministic Outputs

### The mistake

Agents produce random responses because prompts are not controlled.

Example:

```text
sometimes structured
sometimes free text
```

Automation breaks.

### Correct approach

Agents should enforce:

* structured JSON output
* strict prompts
* low temperature

Example:

```json
{
  "priority": "high",
  "duplicate": false,
  "confidence": 0.83
}
```

---

# The Big Architectural Insight

Your architecture is converging toward a **hybrid of three proven systems**.

| Inspiration    | What you are building |
| -------------- | --------------------- |
| CI pipelines   | agent execution model |
| data pipelines | knowledge ingestion   |
| microservices  | event-driven agents   |

This combination is **very powerful**.

---

# What Your System Is Becoming

If implemented well, your platform will essentially be a:

```text
AI-assisted development intelligence system
```

Where agents continuously analyze:

* code
* issues
* discussions
* meetings

And generate insights.

---

# One Strategic Suggestion

Before starting development, define **one clear initial workflow**.

Example:

```text
GitHub Issue Created
      ↓
Issue Triage Agent
      ↓
Context Analysis Agent
      ↓
Summary Report Generated
```

Build the whole system around **one complete pipeline first**.

This dramatically increases the chances of success.

This is one of the **most important architectural ideas** for systems like the one you're building. Many platforms eventually adopt this separation because it keeps the system **maintainable and scalable**.

The idea is to split the system into two parts:

```
Agent Platform
   │
   ├── Control Plane
   └── Data Plane
```

Think of it like how container platforms work internally.

---

# 1. What Is the Control Plane?

The **Control Plane** manages and coordinates the system.

It does **not perform heavy work**.
Instead it controls **what should happen**.

Responsibilities:

```
job scheduling
agent registration
event processing
system configuration
metadata management
execution monitoring
```

In your MVP, the control plane would include:

```
API server
job scheduler
event bus
metadata database
agent registry
```

Example components:

```
FastAPI server
PostgreSQL
event dispatcher
agent runner controller
```

---

# 2. What Is the Data Plane?

The **Data Plane** does the actual work.

This is where **agents run and process data**.

Responsibilities:

```
agent execution
LLM calls
data processing
report generation
artifact creation
```

Components:

```
agent containers
Gemini API calls
knowledge cache
blob storage
```

---

# 3. Visual Architecture

```
                Control Plane
         ┌─────────────────────────┐
         │ API Server              │
         │ Job Scheduler           │
         │ Event Bus               │
         │ Agent Registry          │
         │ Metadata Database       │
         └───────────┬─────────────┘
                     │
                     ▼
                Data Plane
        ┌────────────────────────────┐
        │ Agent Containers           │
        │ Issue Triage Agent         │
        │ PR Context Agent           │
        │ Meeting Summary Agent      │
        │                            │
        │ Gemini Vertex AI API       │
        │ Knowledge Cache (Git)      │
        │ Blob Storage (MinIO)       │
        └────────────────────────────┘
```

---

# 4. How Execution Works

Example job execution.

### Step 1 — Job created

User or event triggers:

```
POST /jobs/run
```

Control plane stores job.

---

### Step 2 — Scheduler picks job

Control plane decides:

```
run issue-triage agent
```

---

### Step 3 — Agent starts

Control plane launches container.

```
docker run issue-triage-agent
```

---

### Step 4 — Data plane runs work

Agent performs:

```
fetch issue
call Gemini
generate report
commit to Git
```

---

### Step 5 — Completion

Agent returns result.

Control plane records metadata.

---

# 5. Why This Separation Matters

Without this separation systems become messy.

Example bad design:

```
agents manage scheduling
agents trigger other agents
agents manage events
```

Eventually:

```
unpredictable behavior
difficult debugging
tight coupling
```

---

# 6. Benefits of Control/Data Plane Architecture

### Stability

Control logic is isolated.

Agents cannot break the system.

---

### Scalability

You can run many agents.

```
control plane
      │
      ▼
multiple data-plane workers
```

---

### Easier debugging

Control plane logs:

```
job lifecycle
agent failures
events
```

---

### Future scalability

Later you could run agents across:

```
multiple machines
Kubernetes
cloud clusters
```

Without redesigning everything.

---

# 7. Mapping This to Your MVP

Your MVP architecture could look like this.

## Control Plane

```
FastAPI server
PostgreSQL
event bus
job scheduler
agent registry
```

## Data Plane

```
agent containers
Gemini API
Git knowledge cache
MinIO storage
```

---

# 8. Minimal Deployment Example

```
Linux VM
│
├── control-plane
│    ├── api-server
│    ├── scheduler
│    └── postgres
│
└── data-plane
     ├── agent-runner
     ├── agents
     └── minio
```

All inside Docker.

---

# 9. Future Evolution

Later you can scale like this.

```
Control Plane
      │
      ▼
Agent Workers
  ├── worker node 1
  ├── worker node 2
  └── worker node 3
```

Each worker runs agents.

---

# 10. Very Important Design Rule

Agents should **never control the system**.

Agents should only:

```
read data
analyze data
generate insights
produce artifacts
```

The **control plane orchestrates everything**.

---

# 11. Where Gemini Fits

Gemini stays purely in the **data plane**.

```
agent
   │
   ▼
Gemini Vertex AI
```

The control plane never calls Gemini directly.

---

# 12. Final Simplified Architecture

Your system ultimately becomes:

```
           Users
             │
             ▼
       Control Plane
             │
             ▼
        Agent Workers
             │
             ▼
         Gemini API
             │
             ▼
         Knowledge Base
```

---

# Final Thought

What you're designing is essentially a **new category of internal developer tool**:

```
AI-native development intelligence platform
```

Below is a **practical 30-day roadmap** to build the MVP of your **Agentic AI platform** using:

* Google Cloud Vertex AI + Gemini
* PostgreSQL
* MinIO
* Git knowledge cache
* Docker containers

The goal of the first month is **not perfection**, but a **working pipeline**:

```
GitHub Issue
     ↓
Agent runs
     ↓
Gemini analysis
     ↓
Report stored in Git
     ↓
Logs visible in UI
```

---

# 30-Day MVP Development Roadmap

## Overall Target Architecture

```
Control Plane
    API server
    job scheduler
    event bus
    PostgreSQL metadata

Data Plane
    agent runner
    agents
    Gemini API
    Git knowledge cache
    MinIO storage
```

---

# Week 1 — Core Infrastructure

Goal: **Get the system skeleton running**

### Day 1–2: Project Setup

Create repository structure.

```
agent-platform/
   api-server/
   agents/
   infrastructure/
   knowledge-cache/
   web-ui/
```

Set up:

```
Docker
Docker Compose
```

Services:

```
postgres
minio
api-server
```

---

### Day 3: Metadata Database

Create PostgreSQL schema.

Core tables:

```
agents
jobs
agent_runs
artifacts
events
```

Example:

```
jobs
-----
id
agent_name
status
created_at
started_at
completed_at
```

---

### Day 4: API Server

Build API server using FastAPI.

Endpoints:

```
POST /jobs/run
GET /jobs
GET /jobs/{id}
GET /agents
```

The API server belongs to the **control plane**.

---

### Day 5: Agent Runner

Create a simple **agent runner service**.

Responsibilities:

```
poll job queue
start agent container
capture logs
update job status
```

Execution flow:

```
API creates job
     ↓
runner detects job
     ↓
runner starts container
```

---

### Day 6–7: Knowledge Cache

Create Git-based knowledge repository.

Structure:

```
knowledge-cache/

github/
issues/

agent_outputs/
issue_analysis/
```

Implement helper library:

```
read knowledge
write reports
commit changes
```

Test committing from code.

---

# Week 2 — First Working Agent

Goal: **Run a real agent using Gemini**

---

### Day 8–9: Gemini Client

Implement a shared LLM client.

Using Vertex AI SDK.

Interface:

```
generate(prompt)
```

Features:

```
retry
logging
token tracking
```

Test with a simple prompt.

---

### Day 10–11: Issue Triage Agent

Create first agent.

Directory:

```
agents/issue-triage-agent/
```

Responsibilities:

```
fetch issue
build prompt
call Gemini
generate report
```

Example output:

```
priority
duplicates
related components
confidence
```

---

### Day 12: Prompt Templates

Create versioned prompt templates.

```
agents/prompts/

issue_analysis.prompt
```

Example prompt:

```
Analyze this GitHub issue.

Determine:
1 priority
2 duplicates
3 affected components
```

Store prompts in Git.

---

### Day 13–14: GitHub Data Ingestion

Implement GitHub fetcher.

Ingest:

```
issues
PR metadata
comments
```

Store locally:

```
knowledge-cache/github/issues/
```

Agents read from this.

---

# Week 3 — Observability + UI

Goal: **Make the system visible and usable**

---

### Day 15–16: Log Streaming

Capture container logs.

Pipeline:

```
agent stdout
     ↓
runner
     ↓
WebSocket
     ↓
web UI
```

Users can watch agent execution live.

Example log stream:

```
Fetching issue #231
Building prompt
Calling Gemini
Generating report
Done
```

---

### Day 17–18: Basic Web Dashboard

Build simple React UI.

Pages:

```
Jobs
Agent runs
Logs viewer
Reports browser
```

Example:

```
Active Jobs
Completed Jobs
```

---

### Day 19: Report Viewer

UI page to view generated reports.

Reports come from:

```
knowledge-cache/agent_outputs/
```

Display:

```
issue summary
priority
related PRs
```

---

### Day 20–21: Event Bus

Implement minimal event system.

Using PostgreSQL.

Event structure:

```
event_type
payload
timestamp
```

Example event:

```
issue.analyzed
```

Agents publish events.

Future agents can subscribe.

---

# Week 4 — Stabilization

Goal: **Make system reliable**

---

### Day 22–23: Artifact Storage

Store large outputs in MinIO.

Example artifacts:

```
LLM responses
long transcripts
attachments
```

Metadata stored in PostgreSQL.

---

### Day 24: LLM Usage Tracking

Add tracking table.

```
llm_usage
---------
run_id
model
tokens_in
tokens_out
cost_estimate
```

Important for cost control.

---

### Day 25–26: Error Handling

Add retry policies.

Handle:

```
Gemini API failures
network errors
timeout
```

Return structured errors.

---

### Day 27: Agent Registration

Implement:

```
POST /agents/register
```

Agents register capabilities.

This allows future discovery.

---

### Day 28–29: System Testing

Test pipeline:

```
create GitHub issue
      ↓
ingestion
      ↓
issue agent
      ↓
Gemini analysis
      ↓
report generated
      ↓
Git commit
```

Verify logs and metadata.

---

### Day 30: MVP Demo

End-to-end demo.

```
GitHub issue
     ↓
agent runs
     ↓
Gemini analysis
     ↓
report visible in dashboard
```

You now have a **working AI-assisted development analysis system**.

---

# What You Will Have After 30 Days

A system that can:

```
ingest GitHub issues
run agents
call Gemini
generate reports
store artifacts
track metadata
stream logs
show results in UI
```

That’s already a **real platform**.

---

# Realistic Code Size

Rough estimate:

```
API server        ~2000 lines
Agent runner      ~1200 lines
Agents            ~1000 lines
Web UI            ~2500 lines
Infrastructure    ~500 lines
```

Total:

```
~7000 lines
```

Very manageable.

---

# What Comes After MVP

Once the MVP works, the next upgrades would be:

1. semantic search memory
2. additional agents
3. Slack integration
4. meeting analysis
5. automated insights

---


Before you start coding, defining a **clean data model** will save a lot of refactoring later. Below is a **minimal but powerful schema** for the MVP that supports:

* job execution
* agent tracking
* event bus
* artifact storage
* Gemini usage tracking
* traceability

The schema is designed for **PostgreSQL**.

---

# 1. Core Data Model Overview

The platform revolves around **five core entities**.

```id="p4c57x"
Agents
Jobs
Agent Runs
Artifacts
Events
```

Relationships:

```id="pjg98c"
Agent
   │
   ▼
Job
   │
   ▼
Agent Run
   │
   ├── Artifacts
   └── LLM Usage
```

And the **event system** connects everything.

---

# 2. Agents Table

Tracks registered agents in the system.

```sql id="z5p2nb"
CREATE TABLE agents (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    version TEXT,
    description TEXT,
    container_image TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

Example record:

```id="3cy9u5"
name: issue-triage
version: 1.0
container_image: agent/issue-triage:latest
```

---

# 3. Jobs Table

Represents a **requested execution**.

Jobs belong to the **control plane**.

```sql id="t8h57o"
CREATE TABLE jobs (
    id SERIAL PRIMARY KEY,
    agent_name TEXT NOT NULL,
    status TEXT,
    parameters JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);
```

Example parameters:

```json id="sihsl3"
{
  "issue_id": 231
}
```

---

# 4. Agent Runs Table

Tracks actual execution details.

```sql id="e0kyfc"
CREATE TABLE agent_runs (
    id SERIAL PRIMARY KEY,
    job_id INTEGER REFERENCES jobs(id),
    agent_name TEXT,
    status TEXT,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    git_commit TEXT,
    logs_uri TEXT
);
```

This enables **full execution history**.

---

# 5. Artifacts Table

Tracks outputs generated by agents.

Artifacts may live in:

* Git
* MinIO
* local files

```sql id="eg1qsu"
CREATE TABLE artifacts (
    id SERIAL PRIMARY KEY,
    run_id INTEGER REFERENCES agent_runs(id),
    artifact_type TEXT,
    storage_uri TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

Example record:

```id="4stztc"
artifact_type: issue_analysis
storage_uri: knowledge-cache/issue_analysis/231.md
```

Or:

```id="1bb5v1"
storage_uri: s3://agent-artifacts/prompts/run123.json
```

---

# 6. Event Bus Table

Implements the **Agent Bus**.

```sql id="25zjsn"
CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    event_type TEXT,
    source TEXT,
    payload JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    processed BOOLEAN DEFAULT FALSE
);
```

Example event:

```json id="fawck9"
{
  "event_type": "issue.analyzed",
  "source": "issue-triage",
  "payload": {
    "issue_id": 231,
    "priority": "high"
  }
}
```

Schedulers watch this table.

---

# 7. LLM Usage Table

Tracks **Gemini API usage**.

```sql id="qg9wpf"
CREATE TABLE llm_usage (
    id SERIAL PRIMARY KEY,
    run_id INTEGER REFERENCES agent_runs(id),
    model TEXT,
    tokens_input INTEGER,
    tokens_output INTEGER,
    latency_ms INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);
```

Example record:

```id="j4c9it"
model: gemini-1.5-pro
tokens_input: 1400
tokens_output: 220
latency: 2100ms
```

This enables cost tracking.

---

# 8. Agent Subscriptions Table

Defines **which agents react to which events**.

```sql id="ysc71d"
CREATE TABLE agent_subscriptions (
    id SERIAL PRIMARY KEY,
    agent_name TEXT,
    event_type TEXT
);
```

Example:

```id="my1t17"
agent_name: pr-context
event_type: issue.analyzed
```

When event occurs → scheduler triggers agent.

---

# 9. Insights Table (Optional Early)

Stores long-term patterns discovered by agents.

```sql id="gdy67k"
CREATE TABLE insights (
    id SERIAL PRIMARY KEY,
    insight_type TEXT,
    description TEXT,
    evidence JSONB,
    confidence FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

Example:

```id="2ltz9k"
type: recurring_bug
component: auth_service
confidence: 0.81
```

---

# 10. Example Full Execution Flow

Let’s walk through a real run.

### Step 1 — Job created

Insert:

```id="stp6p1"
jobs
```

---

### Step 2 — Agent starts

Insert:

```id="jjttso"
agent_runs
```

---

### Step 3 — Gemini called

Insert:

```id="vut7s0"
llm_usage
```

---

### Step 4 — Artifact created

Insert:

```id="84lfvy"
artifacts
```

---

### Step 5 — Event published

Insert:

```id="6q2eav"
events
```

---

# 11. Example Query (Debugging)

Example query to inspect a run.

```sql id="l6x52a"
SELECT
  r.id,
  j.agent_name,
  r.status,
  r.git_commit
FROM agent_runs r
JOIN jobs j ON r.job_id = j.id;
```

Very useful for debugging.

---

# 12. Why This Model Works

This schema supports:

| Feature               | Supported |
| --------------------- | --------- |
| job scheduling        | yes       |
| event-driven agents   | yes       |
| artifact tracking     | yes       |
| Gemini usage tracking | yes       |
| traceability          | yes       |

And it remains **very small and understandable**.

---

# 13. Database Size Expectations

For early usage:

```id="91fwhk"
10–100 agent runs/day
```

PostgreSQL will easily handle this.

Even at:

```id="aqgk7f"
100k runs
```

the database remains small.

---

# 14. Final MVP Storage Layout

```id="r6qk9u"
PostgreSQL
   jobs
   agent_runs
   artifacts
   events
   llm_usage

Git Knowledge Cache
   project knowledge
   agent outputs

MinIO
   large artifacts
```

Clean separation.

---

# Final Advice Before Implementation

When building systems like this, **start with one agent and one pipeline**.

Example:

```id="22xufj"
GitHub Issue
   ↓
Issue Triage Agent
   ↓
Gemini Analysis
   ↓
Report stored in Git
```

Once that works, expand.

---

A **CLI tool for your platform** that allows developers to run agents locally like:

```bash
agent run issue-triage --issue 231
```

This dramatically improves adoption and testing.
