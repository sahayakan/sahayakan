# Research: OpenCode SDK as Runtime Replacement for Sahayakan

**Date**: 2026-03-14
**Status**: Evaluation Complete
**Verdict**: Do NOT replace. Consider as future complement for Phase 3.

---

## What OpenCode SDK Is

**OpenCode** is an open-source AI coding agent (like Claude Code / Cursor) with terminal, desktop, and IDE interfaces. The **SDK** (`@opencode-ai/sdk`, TypeScript/npm) is a type-safe JS client for its server component.

**Key point**: OpenCode is a *coding agent* -- it reads/writes code, runs shell commands, and navigates codebases. It is NOT a general-purpose agent framework.

## SDK Capabilities

| Capability | Details |
|---|---|
| Session management | Create/list/delete sessions, send prompts, get responses |
| Structured output | Request validated JSON via JSON Schema with retries |
| File operations | Search text, discover files, read contents |
| Shell execution | Run shell commands within sessions |
| SSE event stream | Real-time events from agent execution |
| Agent discovery | List available agents via `app.agents()` |
| TUI control | Programmatic prompts, dialogs, toasts |
| Auth | Manage provider credentials |
| Multi-provider | Configure any LLM provider (Anthropic, OpenAI, etc.) |

## Comparison: Sahayakan Runtime vs OpenCode SDK

### What Sahayakan's Runtime Provides

1. **5-stage pipeline**: load_input -> collect_context -> analyze -> generate_output -> store_artifacts
2. **Job queue**: Postgres-backed polling (pending -> running -> completed)
3. **Review gates**: Human-in-the-loop between stages
4. **Knowledge cache**: File-based + git versioning artifact store
5. **Semantic search**: pgvector embeddings for context gathering
6. **LLM abstraction**: Pluggable providers (Gemini, mock)
7. **Cost tracking**: Token counts, latency per run
8. **Event publishing**: DB-backed event stream

### What OpenCode SDK Provides

- A session-based prompt/response loop with an LLM coding agent
- File read/search within a codebase
- Structured JSON output from LLM responses
- SSE events for monitoring

### Gap Analysis

| Sahayakan Feature | OpenCode Equivalent | Gap |
|---|---|---|
| 5-stage pipeline with lifecycle | None (prompt/response only) | **Critical** |
| Postgres job queue + scheduling | None | **Critical** |
| Review gates (human-in-the-loop) | None | **Critical** |
| Knowledge cache (git-versioned) | None | **Critical** |
| Semantic search (pgvector) | None | **Critical** |
| Cost tracking (tokens, latency) | None | **Major** |
| Event bus (DB-backed) | SSE stream (ephemeral) | **Major** |
| LLM abstraction (Python) | Multi-provider (TypeScript) | Language mismatch |
| RBAC + multi-tenancy | None | **Critical** |

## Verdict: NOT a Good Fit as Runtime Replacement

### Reasons

1. **Different paradigm**: OpenCode is a *coding agent* (edit files, run commands). Sahayakan agents are *analytical agents* (triage issues, summarize meetings, detect trends). Square peg, round hole.

2. **No pipeline abstraction**: OpenCode has sessions with prompts, not staged pipelines with gates. Sahayakan's 5-stage lifecycle with review gates has no equivalent.

3. **No job queue**: OpenCode doesn't have a job queue, scheduling, or async batch processing. Sahayakan polls a Postgres job table.

4. **No persistence layer**: OpenCode doesn't persist artifacts to a knowledge cache or track them in a database. Sahayakan has git-versioned artifact storage.

5. **No semantic search**: No pgvector, no embedding-based context gathering.

6. **Language mismatch**: SDK is TypeScript-only. Sahayakan is Python. Would require a full rewrite of 12 stages of work.

7. **No cost tracking**: No built-in token/latency metrics per agent run.

8. **Maturity**: OpenCode's documentation is sparse with many 404 pages. The SDK is young with limited community adoption.

## Future Consideration: Code Intelligence Complement (Phase 3)

OpenCode SDK could be valuable as a **complement** (not replacement) when Stage 13 (Code Intelligence) is implemented. It could power:

1. **Code Review Agent**: Send PR diffs to an OpenCode session, get structured code review feedback as JSON
2. **Codebase Q&A**: Use OpenCode sessions to answer questions about a project's codebase
3. **Automated Fixes**: Given an issue analysis from Issue Triage, spin up an OpenCode session to propose a fix
4. **Dependency Analysis**: Use OpenCode's file search to analyze dependency trees

### Integration Architecture (If Pursued)

```
Sahayakan Agent Runner (Python)
  |
  +-- Existing Agents (Python, BaseAgent)
  |   +-- Issue Triage
  |   +-- PR Context
  |   +-- Meeting Summary
  |   +-- Slack Digest
  |   +-- Insights
  |   +-- Trend Analysis
  |
  +-- Code Intelligence Bridge (New)
      |
      +-- OpenCode server on localhost
      |
      +-- Python HTTP client (httpx) calling OpenCode API
          +-- create_session(project_path)
          +-- prompt(session_id, question, schema) -> structured JSON
          +-- search_code(session_id, query) -> results
          +-- cleanup_session(session_id)
```

### Implementation Options

| Option | Approach | Pros | Cons |
|---|---|---|---|
| **A: HTTP-direct** (recommended) | Python `httpx` client calling OpenCode HTTP API | Simple, no language bridge | Must reverse-engineer API from SDK types |
| B: Node.js sidecar | Small Node script using `@opencode-ai/sdk`, called via subprocess | Uses official SDK | Adds Node.js dependency |
| C: MCP bridge | Expose KnowledgeCache as MCP server for OpenCode | Standard protocol, bidirectional | More complex setup |

## Recommendation

1. **Do not replace** the current Sahayakan runtime with OpenCode SDK
2. **Keep the current architecture** -- it is purpose-built for analytical agent workflows
3. **Revisit OpenCode** when implementing Stage 13 (Code Intelligence) as a potential tool for the Code Review Agent
4. **Preferred integration**: Option A (HTTP-direct) -- write a thin Python `httpx` wrapper around OpenCode's HTTP API

## Sources

- OpenCode SDK documentation: https://opencode.ai/docs/sdk/
- OpenCode main documentation: https://opencode.ai/docs/
- Sahayakan codebase: BaseAgent, AgentRunner, LLM Client, KnowledgeCache
- Phase 3 plan: `docs/PHASE_3_PLAN.md` (Stage 13: Code Intelligence)
