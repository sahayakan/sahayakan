-- Stage 10: Insights Engine

CREATE TABLE insights (
    id SERIAL PRIMARY KEY,
    insight_type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    evidence JSONB,
    severity TEXT DEFAULT 'medium',
    confidence FLOAT DEFAULT 0.0,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_insights_type ON insights(insight_type);
CREATE INDEX idx_insights_status ON insights(status);
CREATE INDEX idx_insights_severity ON insights(severity);
