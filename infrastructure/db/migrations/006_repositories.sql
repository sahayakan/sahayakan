CREATE TABLE repositories (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    url TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT 'github',
    default_branch TEXT NOT NULL DEFAULT 'main',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_repositories_provider ON repositories(provider);
CREATE INDEX idx_repositories_active ON repositories(is_active);
