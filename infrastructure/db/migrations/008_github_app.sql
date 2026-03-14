-- GitHub App integration tables
CREATE TABLE IF NOT EXISTS github_apps (
    id SERIAL PRIMARY KEY,
    app_id INTEGER NOT NULL UNIQUE,
    app_name TEXT NOT NULL,
    private_key_encrypted TEXT NOT NULL,
    webhook_secret TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS github_app_installations (
    id SERIAL PRIMARY KEY,
    github_app_id INTEGER REFERENCES github_apps(id) ON DELETE CASCADE,
    installation_id INTEGER NOT NULL UNIQUE,
    account_login TEXT NOT NULL,
    account_type TEXT NOT NULL DEFAULT 'Organization',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

ALTER TABLE repositories
    ADD COLUMN IF NOT EXISTS github_installation_id INTEGER REFERENCES github_app_installations(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS auth_mode TEXT NOT NULL DEFAULT 'pat';
