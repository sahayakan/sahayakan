-- Stage 9: Scheduled Automation

CREATE TABLE schedules (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    agent_name TEXT REFERENCES agents(name),
    schedule_type TEXT NOT NULL,       -- 'agent_job', 'github_sync', 'jira_sync', 'slack_sync'
    cron_expression TEXT NOT NULL,
    parameters JSONB,
    enabled BOOLEAN DEFAULT TRUE,
    last_run_at TIMESTAMP,
    next_run_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_schedules_enabled ON schedules(enabled);
CREATE INDEX idx_schedules_next_run ON schedules(next_run_at);
