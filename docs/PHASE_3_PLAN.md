# Sahayakan - Phase 3 Master Plan

## Context

Phase 1 delivered a working agent platform with 3 agents, event orchestration, and a web dashboard. Phase 2 evolved it into a production-grade system with semantic memory, Slack integration, scheduling, pattern detection, authentication, and Kubernetes deployment.

Phase 3 transforms Sahayakan from a **report-generating tool** into an **interactive AI development intelligence system** — agents that understand code, converse with developers, learn from feedback, and take supervised actions.

## Phase 3 Vision

> Developers interact with Sahayakan as naturally as they interact with a teammate — asking questions in Slack, getting proactive suggestions in PRs, and trusting the system to handle routine work autonomously while escalating what matters.

## Phase 3 Goals

1. **Code intelligence** — Agents read, understand, and analyze actual source code
2. **Conversational interface** — Developers chat with agents via Slack or web UI
3. **Multi-model support** — Use Claude, GPT-4, and Gemini based on task requirements
4. **Agent plugins** — Third parties can add custom agents without modifying core
5. **Knowledge graph** — Structured relationships between people, components, issues, and PRs
6. **Actionable agents** — Agents can create issues, post PR comments, update Jira (with approval)
7. **Learning from feedback** — Agents improve over time using human review decisions

## Phase 3 Architecture

```
            Developers / Slack Bot / GitHub App / Web UI
                              |
                              v
                  +----- Control Plane -------+
                  | API Server + Auth         |
                  | Conversational Gateway    |
                  | Plugin Registry           |
                  | Scheduler + Webhooks      |
                  +-------------+-------------+
                                |
                                v
                  +------- Data Plane --------+
                  | Agent Runner              |
                  | Code Review Agent (new)   |
                  | Chat Agent (new)          |
                  | Action Agent (new)        |
                  | Plugin Agents (dynamic)   |
                  | 6 existing agents         |
                  |                           |
                  | Multi-Model LLM Router    |
                  | Knowledge Graph (Neo4j)   |
                  | Vector Store (pgvector)   |
                  | Code Index (tree-sitter)  |
                  +---------------------------+
```

## Phase 3 Stages

| Stage | Name                        | Description                                                     |
| ----- | --------------------------- | --------------------------------------------------------------- |
| 13    | Code Intelligence           | Code indexing, code review agent, repository-aware analysis     |
| 14    | Multi-Model LLM Router      | Claude + GPT-4 + Gemini with task-based routing                 |
| 15    | Conversational Interface    | Chat with agents via Slack bot and web UI                       |
| 16    | Knowledge Graph             | Entity relationships, dependency mapping, impact analysis       |
| 17    | Actionable Agents           | Create issues, post PR comments, update Jira with approval      |
| 18    | Agent Plugin System         | Dynamic agent loading, plugin API, marketplace                  |
| 19    | Learning & Feedback Loop    | Improve agents from review decisions, prompt tuning             |
| 20    | Advanced Analytics          | Team dashboards, sprint analytics, developer experience metrics |

---

## Stage 13: Code Intelligence

### Goal

Agents can read and understand source code. A new Code Review Agent analyzes PRs at the code level — reviewing diffs, detecting bugs, suggesting improvements.

### Tasks

**13.1 Code Indexing Service**

Index repository source code for agent consumption:

- Clone target repositories into a managed workspace
- Parse code using tree-sitter for language-aware analysis
- Build a file/function/class index stored in PostgreSQL
- Incremental re-indexing on push events

```sql
CREATE TABLE code_index (
    id SERIAL PRIMARY KEY,
    repo TEXT NOT NULL,
    file_path TEXT NOT NULL,
    language TEXT,
    symbols JSONB,           -- functions, classes, imports
    content_hash TEXT,
    last_indexed_at TIMESTAMP,
    UNIQUE(repo, file_path)
);
```

**13.2 Code Review Agent**

New agent that performs code-level PR review:

- Input: PR number + repository
- Fetches PR diff via GitHub API
- Analyzes changed files against codebase context
- Detects: potential bugs, security issues, style violations, missing tests, complexity
- Produces line-by-line review comments

Output:
```json
{
  "pr_number": 143,
  "review_verdict": "changes_requested",
  "comments": [
    {
      "file": "auth/oauth.py",
      "line": 42,
      "severity": "warning",
      "category": "security",
      "comment": "Token is logged in plaintext. Use redacted logging.",
      "suggestion": "logger.info(f'Token refreshed: {token[:8]}...')"
    }
  ],
  "summary": "2 security issues, 1 missing test",
  "confidence": 0.81
}
```

**13.3 Repository Configuration**

```yaml
repositories:
  - url: https://github.com/org/project
    branch: main
    languages: [python, javascript]
    index_schedule: "*/30 * * * *"
    review_on_pr: true
```

**13.4 Code-Aware Context**

Enhance existing agents with code awareness:
- Issue Triage Agent: map issues to affected source files
- PR Context Agent: include function-level change analysis
- Insights Agent: detect code hotspots (files with most bugs)

### Deliverables

- [ ] Code indexing service with tree-sitter parsing
- [ ] Code Review Agent with line-by-line comments
- [ ] PR diff analysis with security/bug/style detection
- [ ] Existing agents enhanced with code context

---

## Stage 14: Multi-Model LLM Router

### Goal

Use the best LLM for each task. Route requests to Claude, GPT-4, or Gemini based on task type, cost constraints, and performance.

### Tasks

**14.1 LLM Router**

```python
class LLMRouter:
    def route(self, task_type: str, prompt: str) -> LLMClient:
        """Select the best model for this task."""
        # code_review -> Claude (best at code analysis)
        # summarization -> Gemini Flash (fast, cheap)
        # deep_analysis -> GPT-4 or Claude (highest quality)
        # embedding -> Gemini Embedding API
```

**14.2 Provider Implementations**

Add new LLM providers alongside existing Gemini:

- `ClaudeClient` — Anthropic Claude API (claude-sonnet-4-20250514, claude-haiku-4-5-20251001)
- `OpenAIClient` — OpenAI API (gpt-4o, gpt-4o-mini)
- `GeminiClient` — existing Vertex AI client

All implement the same `LLMClient` interface.

**14.3 Routing Rules**

| Task Type | Primary Model | Fallback |
|-----------|--------------|----------|
| Code review | Claude Sonnet | GPT-4o |
| Issue analysis | Gemini Pro | Claude Sonnet |
| PR summary | Gemini Flash | GPT-4o-mini |
| Meeting summary | Gemini Pro | Claude Sonnet |
| Slack digest | Gemini Flash | GPT-4o-mini |
| Insights | Claude Sonnet | Gemini Pro |
| Embedding | Gemini Embedding | OpenAI Embedding |

**14.4 Cost Optimization**

- Automatic model downgrade when budget is exceeded
- Per-team cost budgets
- Model performance comparison logging

### Deliverables

- [ ] LLMRouter with task-based model selection
- [ ] Claude and OpenAI client implementations
- [ ] Routing rules configurable per-agent
- [ ] Cost-aware model selection with budget enforcement

---

## Stage 15: Conversational Interface

### Goal

Developers interact with agents through natural language — asking questions in Slack, getting answers from the knowledge base, and triggering agent runs conversationally.

### Tasks

**15.1 Slack Bot (Interactive)**

Upgrade from notification-only to interactive:

```
Developer: @sahayakan what's the status of auth timeout issues?
Sahayakan: I found 3 related issues (#231, #198, #2800). Issue #231 is
           high priority with a fix in PR #143. Want me to run a fresh
           analysis?
Developer: yes, analyze #231
Sahayakan: Running issue triage on #231... [live progress]
           Analysis complete: Priority HIGH, likely regression from PR #120.
           Full report: [link]
```

Features:
- Slash commands: `/sahayakan analyze #231`, `/sahayakan digest #engineering`
- Mention handler: `@sahayakan <question>`
- Thread-aware: replies stay in the same thread
- Interactive buttons: approve/reject reviews from Slack

**15.2 Web Chat Interface**

Chat panel in the web UI:

- Natural language queries against the knowledge base
- Semantic search integrated into responses
- Run agents from chat: "analyze PR #143"
- Show agent progress inline

**15.3 Query Understanding Agent**

New agent that interprets natural language queries:

- Classifies intent: search, analyze, report, status
- Extracts entities: issue numbers, PR numbers, component names
- Routes to appropriate agent or search
- Synthesizes answers from multiple sources

**15.4 RAG Pipeline**

Retrieval-Augmented Generation for answering questions:

```
User question
    |
    v
Semantic search (pgvector)
    |
    v
Retrieve top-K relevant documents
    |
    v
Build context prompt with retrieved docs
    |
    v
LLM generates answer
    |
    v
Response with source citations
```

### Deliverables

- [ ] Interactive Slack bot with mentions, slash commands, threads
- [ ] Web chat interface with inline agent execution
- [ ] Query understanding agent for intent classification
- [ ] RAG pipeline for knowledge-based Q&A with citations

---

## Stage 16: Knowledge Graph

### Goal

Build structured relationships between entities — people, components, issues, PRs, meetings — to enable impact analysis, dependency tracking, and organizational insights.

### Tasks

**16.1 Graph Database**

Add Neo4j or use PostgreSQL with recursive CTEs:

Entity types:
- `Person` (developer, reviewer, assignee)
- `Component` (module, service, file)
- `Issue` (GitHub issue)
- `PullRequest` (GitHub PR)
- `JiraTicket`
- `Meeting`
- `Insight`

Relationships:
- `Person -[AUTHORED]-> PullRequest`
- `Person -[ASSIGNED]-> Issue`
- `PullRequest -[FIXES]-> Issue`
- `PullRequest -[MODIFIES]-> Component`
- `Issue -[AFFECTS]-> Component`
- `Meeting -[DISCUSSED]-> Issue`
- `Insight -[EVIDENCED_BY]-> Issue`

**16.2 Graph Builder**

Automatically populate the graph from:
- GitHub data (issues, PRs, commits, reviews)
- Agent outputs (linked issues, affected components)
- Meeting summaries (mentioned issues, attendees)

**16.3 Impact Analysis**

Query the graph to answer:
- "What will be affected if we change component X?"
- "Who has context on this area of code?"
- "What issues are related to this PR through shared components?"

**16.4 Graph Visualization**

Interactive graph visualization in the web UI:
- Explore entity relationships
- Filter by type, time range, team
- Highlight impact paths

### Deliverables

- [ ] Entity-relationship schema for development knowledge
- [ ] Graph builder from existing data sources
- [ ] Impact analysis queries
- [ ] Interactive graph visualization in web UI

---

## Stage 17: Actionable Agents

### Goal

Agents can take actions in external systems — creating issues, posting PR review comments, updating Jira tickets — always with approval when configured.

### Tasks

**17.1 Action Framework**

```python
class AgentAction:
    action_type: str     # 'create_issue', 'post_pr_comment', 'update_jira'
    target: dict         # action-specific target
    payload: dict        # action content
    requires_approval: bool
```

Actions flow through the review gate system:
```
Agent proposes action
    |
    v
[Review gate if enabled]
    |
    v
Action executor performs action
    |
    v
Audit log records action + result
```

**17.2 GitHub Actions**

- Create issues from insights (e.g., "Recurring bug detected → create tracking issue")
- Post PR review comments from Code Review Agent
- Add labels based on issue triage
- Close duplicate issues (with approval)

**17.3 Jira Actions**

- Create tickets from meeting action items
- Update ticket status from PR merges
- Link Jira tickets to GitHub issues

**17.4 Slack Actions**

- Create channels for incidents
- Post threaded updates on long-running issues
- Tag relevant people based on component ownership

### Deliverables

- [ ] Action framework with approval workflow
- [ ] GitHub actions: create issues, post PR comments, add labels
- [ ] Jira actions: create/update tickets
- [ ] All actions recorded in audit log

---

## Stage 18: Agent Plugin System

### Goal

Allow custom agents to be added to the platform without modifying core code. Teams can build domain-specific agents.

### Tasks

**18.1 Plugin API**

```python
# Plugin manifest (plugin.yaml)
name: security-scanner
version: 1.0
description: Scans PRs for security vulnerabilities
triggers:
  - event: pr.ingested
parameters:
  - name: severity_threshold
    type: string
    default: medium
```

**18.2 Dynamic Agent Loading**

- Agents loaded from a plugins directory or registry
- Each plugin is a Python package with a standard entry point
- Plugins declare their triggers, parameters, and output format
- Plugin isolation via separate processes or containers

**18.3 Plugin Registry**

- API to install, enable, disable, configure plugins
- Plugin marketplace (future): share agents across teams
- Version management and rollback

**18.4 Plugin SDK**

Developer toolkit for building plugins:
- `sahayakan-sdk` package with base classes
- CLI for scaffolding: `sahayakan plugin create my-agent`
- Testing harness for local development
- Documentation generator

### Deliverables

- [ ] Plugin manifest format and loading mechanism
- [ ] Dynamic agent registration from plugins directory
- [ ] Plugin management API (install, enable, configure)
- [ ] Plugin SDK with scaffolding CLI

---

## Stage 19: Learning & Feedback Loop

### Goal

Agents improve over time by learning from human review decisions, prompt adjustments, and outcome tracking.

### Tasks

**19.1 Feedback Collection**

Track when humans:
- Override agent priority suggestions
- Reject agent recommendations
- Modify agent-generated labels
- Approve vs. reject at review gates

```sql
CREATE TABLE feedback (
    id SERIAL PRIMARY KEY,
    agent_name TEXT,
    run_id INTEGER,
    feedback_type TEXT,    -- 'override', 'correction', 'approval', 'rejection'
    original_value JSONB,
    corrected_value JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**19.2 Prompt Tuning**

- Analyze feedback to identify systematic errors
- A/B test prompt variations
- Track prompt version performance over time
- Auto-suggest prompt improvements based on correction patterns

**19.3 Accuracy Tracking**

Dashboard showing:
- Agent accuracy over time (% of suggestions accepted)
- Common correction patterns
- Confidence calibration (does 80% confidence = 80% accuracy?)
- Per-agent improvement trends

**19.4 Few-Shot Learning**

- Store exemplary human corrections as few-shot examples
- Include relevant examples in prompts for similar future cases
- Automatic example selection based on semantic similarity

### Deliverables

- [ ] Feedback collection from review decisions
- [ ] Prompt A/B testing framework
- [ ] Accuracy tracking dashboard
- [ ] Few-shot example injection in prompts

---

## Stage 20: Advanced Analytics

### Goal

Comprehensive engineering analytics dashboard with team performance, sprint metrics, and developer experience insights.

### Tasks

**20.1 Team Dashboard**

- Issues opened/closed per team member (trend)
- PR review turnaround time
- Code review thoroughness score
- Meeting action item completion rate

**20.2 Sprint Analytics**

- Velocity tracking (issues completed per sprint)
- Scope creep detection (issues added mid-sprint)
- Burndown chart generation
- Sprint retrospective auto-summary

**20.3 Developer Experience Metrics**

- Time from issue creation to first response
- PR time-to-merge distribution
- Build failure rate and recovery time
- Documentation coverage score

**20.4 Custom Reports**

- Report builder in web UI (select metrics, time range, team)
- Scheduled report delivery via Slack/email
- Export to PDF/CSV
- Shareable report links

### Deliverables

- [ ] Team performance dashboard with historical trends
- [ ] Sprint analytics with velocity and burndown
- [ ] Developer experience metrics
- [ ] Custom report builder with export and scheduling

---

## Phase 3 Technology Additions

| Component | Technology | Stage |
|-----------|-----------|-------|
| Code Parsing | tree-sitter | 13 |
| Claude API | Anthropic SDK | 14 |
| OpenAI API | OpenAI SDK | 14 |
| Slack Bot (interactive) | Slack Bolt | 15 |
| RAG Pipeline | Custom (pgvector + LLM) | 15 |
| Knowledge Graph | Neo4j or PostgreSQL CTEs | 16 |
| Graph Visualization | D3.js or vis.js | 16 |
| Plugin System | Dynamic Python loading | 18 |
| A/B Testing | Custom framework | 19 |

## Phase 3 New Agents

| Agent | Stage | Purpose |
|-------|-------|---------|
| Code Review Agent | 13 | Line-by-line PR review with bug/security detection |
| Chat Agent | 15 | Natural language query understanding and routing |
| Action Agent | 17 | Executes approved actions in GitHub/Jira/Slack |

## Success Criteria

Phase 3 is complete when:

1. Agents understand source code and provide line-level PR review comments
2. Developers can ask questions and trigger agents via natural language in Slack
3. Multiple LLM providers are used based on task requirements and cost
4. The knowledge graph maps relationships between people, code, and issues
5. Agents can take supervised actions in external systems
6. Custom agents can be added via the plugin system without modifying core
7. Agents measurably improve over time through feedback learning
8. Teams have comprehensive analytics dashboards for engineering metrics
