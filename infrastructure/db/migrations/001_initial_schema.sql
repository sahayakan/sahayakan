-- Sahayakan MVP: Initial Schema
-- Creates all core tables for the agent platform

-- Enum types
CREATE TYPE job_status AS ENUM (
    'pending', 'running', 'completed', 'failed',
    'cancelled', 'awaiting_review'
);

CREATE TYPE run_status AS ENUM (
    'started', 'collecting_data', 'analyzing',
    'generating_output', 'storing_artifacts',
    'completed', 'failed', 'awaiting_review'
);

-- Agents: registered agents in the system
CREATE TABLE agents (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    version TEXT NOT NULL DEFAULT '1.0',
    description TEXT,
    container_image TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Jobs: requested executions (control plane)
CREATE TABLE jobs (
    id SERIAL PRIMARY KEY,
    agent_name TEXT NOT NULL REFERENCES agents(name),
    status job_status DEFAULT 'pending',
    parameters JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Agent runs: actual execution records
CREATE TABLE agent_runs (
    id SERIAL PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES jobs(id),
    agent_name TEXT NOT NULL,
    status run_status DEFAULT 'started',
    start_time TIMESTAMP DEFAULT NOW(),
    end_time TIMESTAMP,
    git_commit TEXT,
    logs_uri TEXT
);

-- Artifacts: outputs from agent runs
CREATE TABLE artifacts (
    id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES agent_runs(id),
    artifact_type TEXT NOT NULL,
    storage_uri TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Events: agent bus
CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    event_type TEXT NOT NULL,
    source TEXT NOT NULL,
    payload JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    processed BOOLEAN DEFAULT FALSE
);

-- LLM usage: Gemini API tracking
CREATE TABLE llm_usage (
    id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES agent_runs(id),
    model TEXT NOT NULL,
    tokens_input INTEGER,
    tokens_output INTEGER,
    latency_ms INTEGER,
    estimated_cost DECIMAL(10, 6),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Agent subscriptions: event subscriptions
CREATE TABLE agent_subscriptions (
    id SERIAL PRIMARY KEY,
    agent_name TEXT NOT NULL REFERENCES agents(name),
    event_type TEXT NOT NULL,
    UNIQUE(agent_name, event_type)
);

-- Review gates: optional human review configuration
CREATE TABLE review_gates (
    id SERIAL PRIMARY KEY,
    agent_name TEXT NOT NULL REFERENCES agents(name),
    stage TEXT NOT NULL,
    enabled BOOLEAN DEFAULT FALSE,
    UNIQUE(agent_name, stage)
);

-- Review decisions: human review actions
CREATE TABLE review_decisions (
    id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES agent_runs(id),
    stage TEXT NOT NULL,
    decision TEXT NOT NULL,
    reviewer TEXT,
    comments TEXT,
    decided_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_agent ON jobs(agent_name);
CREATE INDEX idx_runs_job ON agent_runs(job_id);
CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_processed ON events(processed);
CREATE INDEX idx_llm_usage_run ON llm_usage(run_id);
