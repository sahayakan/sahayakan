-- Stage 7: Semantic Memory - pgvector and embeddings table

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE embeddings (
    id SERIAL PRIMARY KEY,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    embedding vector(768),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(source_type, source_id)
);

CREATE INDEX idx_embeddings_source ON embeddings(source_type, source_id);
