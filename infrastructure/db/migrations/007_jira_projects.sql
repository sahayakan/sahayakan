CREATE TABLE jira_projects (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    project_key TEXT UNIQUE NOT NULL,
    base_url TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_jira_projects_active ON jira_projects(is_active);
CREATE INDEX idx_jira_projects_key ON jira_projects(project_key);
