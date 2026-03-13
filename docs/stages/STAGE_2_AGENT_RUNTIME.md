# Stage 2: Agent Runtime

## Goal

Build the agent execution engine: the agent contract, Docker-based runner, shared LLM client, and the review gate mechanism. After this stage, you can execute a dummy agent end-to-end through the system.

## Dependencies

- Stage 1 completed (infrastructure running, schema applied, API scaffold)

## Tasks

### 2.1 Agent Execution Contract

Define the base agent interface that all agents must implement.

`data-plane/agent-runner/contracts/base_agent.py`:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

@dataclass
class AgentInput:
    job_id: str
    agent_name: str
    source: str
    parameters: dict

@dataclass
class AgentOutput:
    status: str          # "success" or "error"
    summary: str
    data: dict
    artifacts: list[dict]

class BaseAgent(ABC):

    @abstractmethod
    def load_input(self, input: AgentInput) -> None:
        """Load and validate input data."""

    @abstractmethod
    def collect_context(self) -> None:
        """Gather related context from knowledge cache."""

    @abstractmethod
    def analyze(self) -> None:
        """Perform LLM-powered analysis."""

    @abstractmethod
    def generate_output(self) -> AgentOutput:
        """Produce structured output."""

    @abstractmethod
    def store_artifacts(self, output: AgentOutput) -> list[str]:
        """Store artifacts in knowledge cache and/or MinIO."""
```

Execution order enforced by the runner:

```
load_input -> collect_context -> analyze -> generate_output -> store_artifacts
```

### 2.2 Agent Runner Service

The runner is the core of the data plane. It:

1. Polls PostgreSQL for `pending` jobs
2. Launches agent containers (or runs agents in-process for MVP simplicity)
3. Manages the agent lifecycle
4. Captures logs to stdout
5. Updates job/run status in the database
6. Commits results to the knowledge cache
7. Publishes events

`data-plane/agent-runner/runner.py`:

**Runner loop:**

```
while running:
    job = poll_pending_jobs()
    if job:
        update_job_status(job, 'running')
        create_agent_run(job)

        try:
            agent = load_agent(job.agent_name)
            input = build_input(job)

            log("Loading input")
            agent.load_input(input)
            check_review_gate(job, 'after_input')

            log("Collecting context")
            agent.collect_context()
            check_review_gate(job, 'after_context')

            log("Analyzing")
            agent.analyze()
            check_review_gate(job, 'after_analysis')

            log("Generating output")
            output = agent.generate_output()
            check_review_gate(job, 'after_output')

            log("Storing artifacts")
            uris = agent.store_artifacts(output)

            commit_to_knowledge_cache(job, output)
            record_artifacts(run, uris)
            update_run_status(run, 'completed')
            update_job_status(job, 'completed')
            publish_event(job, output)

        except Exception as e:
            update_run_status(run, 'failed')
            update_job_status(job, 'failed')
            log_error(e)

    sleep(poll_interval)
```

**Review gate check:**

```python
def check_review_gate(job, stage):
    gate = get_review_gate(job.agent_name, stage)
    if gate and gate.enabled:
        update_run_status(run, 'awaiting_review')
        update_job_status(job, 'awaiting_review')
        wait_for_review_decision(run, stage)
        # Resumes when human approves or rejects
```

### 2.3 Shared LLM Client (Gemini)

`data-plane/llm-client/gemini_client.py`:

```python
class LLMClient(ABC):
    @abstractmethod
    def generate(self, prompt: str, model: str = None) -> LLMResponse:
        pass

class GeminiClient(LLMClient):
    def __init__(self, project, location):
        self.project = project
        self.location = location

    def generate(self, prompt, model="gemini-1.5-pro"):
        # Call Vertex AI
        # Log: model, tokens_input, tokens_output, latency
        # Return structured response
        pass
```

Features:
- Retry with exponential backoff (max 3 retries)
- Token counting and logging
- Latency measurement
- Structured response parsing

### 2.4 Knowledge Cache Library

`data-plane/agent-runner/knowledge.py`:

Helper functions for interacting with the Git knowledge cache:

```python
def read_file(path: str) -> str:
    """Read a file from the knowledge cache."""

def write_file(path: str, content: str) -> None:
    """Write a file to the knowledge cache."""

def commit(message: str, files: list[str]) -> str:
    """Commit files and return the commit hash."""

def list_files(directory: str) -> list[str]:
    """List files in a knowledge cache directory."""
```

Commit message format:

```
[AI-Agent] {agent_name}: {summary}

Agent: {agent_name}
Job ID: {job_id}
Source: {input_source}
Timestamp: {iso_timestamp}
```

### 2.5 Structured Logging

All agents and the runner use structured logging:

```
[INFO]  [{timestamp}] [{job_id}] {message}
[LLM]   [{timestamp}] [{job_id}] model={model} tokens={n} latency={ms}ms
[ERROR] [{timestamp}] [{job_id}] {error_message}
[GATE]  [{timestamp}] [{job_id}] stage={stage} status=awaiting_review
```

Logs are written to stdout and captured by the runner for streaming.

### 2.6 Dummy Agent for Testing

Create a simple test agent that validates the entire pipeline:

`data-plane/agents/dummy/agent.py`:

- `load_input`: Accepts any input
- `collect_context`: No-op
- `analyze`: Returns a static response (no LLM call)
- `generate_output`: Returns `{"status": "success", "summary": "dummy test"}`
- `store_artifacts`: Writes a test file to knowledge cache

### 2.7 Agent Dockerfile Template

```dockerfile
FROM python:3.12-slim

WORKDIR /agent
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ENV JOB_ID=""
ENV AGENT_NAME=""
ENV KNOWLEDGE_REPO_PATH="/knowledge-cache"
ENV POSTGRES_URI=""

CMD ["python", "agent.py"]
```

### 2.8 Runner API Endpoints

Add to the API server:

```
POST /jobs/{id}/review          -> submit review decision (approve/reject)
GET  /jobs/{id}/review-status   -> check if job is awaiting review
GET  /agents/{name}/gates       -> list review gates for an agent
PUT  /agents/{name}/gates       -> configure review gates
```

## Deliverables

- [ ] `BaseAgent` abstract class defined with standard interface
- [ ] Agent runner polls for jobs and executes agents
- [ ] `GeminiClient` connects to Vertex AI with retry logic
- [ ] Knowledge cache library reads/writes/commits files
- [ ] Structured logging implemented
- [ ] Dummy agent runs end-to-end: job created -> agent runs -> output committed to Git -> job completed
- [ ] Review gate system pauses execution when gates are enabled
- [ ] Review API endpoints allow approving/rejecting paused jobs

## Definition of Done

You can create a job via `POST /jobs/run` with the dummy agent, the runner picks it up, executes it, commits a result to the knowledge cache, and the job shows `completed` status. If a review gate is enabled, the job pauses at the configured stage until approved via the API.
