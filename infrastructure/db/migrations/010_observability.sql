-- 010: Observability improvements
-- Adds request tracing column and persistent job logs table

-- Request tracing: store X-Request-ID on jobs
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS request_id TEXT;

-- Persistent log storage
CREATE TABLE IF NOT EXISTS job_logs (
    id BIGSERIAL PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    stage TEXT DEFAULT '',
    request_id TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_job_logs_job_id ON job_logs(job_id);
CREATE INDEX IF NOT EXISTS idx_job_logs_created ON job_logs(created_at);
