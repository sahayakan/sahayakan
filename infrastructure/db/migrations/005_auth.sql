-- Stage 11: Authentication & Multi-tenancy

CREATE TABLE teams (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE api_keys (
    id SERIAL PRIMARY KEY,
    key_hash TEXT NOT NULL UNIQUE,
    key_prefix TEXT NOT NULL,
    name TEXT NOT NULL,
    team_id INTEGER REFERENCES teams(id),
    scopes TEXT[] DEFAULT ARRAY['read','write'],
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP,
    enabled BOOLEAN DEFAULT TRUE
);

CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    api_key_id INTEGER REFERENCES api_keys(id),
    team_id INTEGER REFERENCES teams(id),
    action TEXT NOT NULL,
    resource TEXT,
    resource_id TEXT,
    details JSONB,
    ip_address TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Add team_id to existing tables (nullable for backward compatibility)
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS team_id INTEGER REFERENCES teams(id);
ALTER TABLE agents ADD COLUMN IF NOT EXISTS team_id INTEGER REFERENCES teams(id);
ALTER TABLE events ADD COLUMN IF NOT EXISTS team_id INTEGER REFERENCES teams(id);
ALTER TABLE insights ADD COLUMN IF NOT EXISTS team_id INTEGER REFERENCES teams(id);
ALTER TABLE schedules ADD COLUMN IF NOT EXISTS team_id INTEGER REFERENCES teams(id);

-- Indexes
CREATE INDEX idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX idx_api_keys_team ON api_keys(team_id);
CREATE INDEX idx_audit_log_team ON audit_log(team_id);
CREATE INDEX idx_audit_log_created ON audit_log(created_at);
CREATE INDEX idx_jobs_team ON jobs(team_id);
