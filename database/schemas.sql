-- Reference Manager Database Schema Extensions
-- For: PiyP Reference Manager System
-- Date: October 19, 2024
-- Purpose: Extend existing PiyP database with Reference Manager specific tables

-- Collections for organizing papers
CREATE TABLE IF NOT EXISTS collections (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, name)
);

-- Many-to-many relationship between collections and papers
CREATE TABLE IF NOT EXISTS collection_papers (
    collection_id INT REFERENCES collections(id) ON DELETE CASCADE,
    paper_id TEXT NOT NULL, -- References research_papers(paper_id)
    added_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (collection_id, paper_id)
);

-- Reading status and user interactions with papers
CREATE TABLE IF NOT EXISTS paper_reading_status (
    paper_id TEXT PRIMARY KEY, -- References research_papers(paper_id)
    user_id TEXT NOT NULL,
    status TEXT CHECK (status IN ('to_read', 'reading', 'read', 'skimmed', 'abandoned')),
    starred BOOLEAN DEFAULT FALSE,
    rating INT CHECK (rating >= 1 AND rating <= 5),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- User-defined tags for papers
CREATE TABLE IF NOT EXISTS tags (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    tag_name TEXT NOT NULL,
    color TEXT, -- Hex color for UI display
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, tag_name)
);

-- Many-to-many relationship between papers and tags
CREATE TABLE IF NOT EXISTS paper_tags (
    paper_id TEXT NOT NULL, -- References research_papers(paper_id)
    tag_id INT REFERENCES tags(id) ON DELETE CASCADE,
    added_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (paper_id, tag_id)
);

-- Async task tracking for long-running operations
CREATE TABLE IF NOT EXISTS async_tasks (
    task_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    task_type TEXT NOT NULL CHECK (task_type IN ('download', 'ingest', 'expansion', 'export', 'upload')),
    status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    progress FLOAT DEFAULT 0.0 CHECK (progress >= 0 AND progress <= 1),
    total_items INT,
    completed_items INT DEFAULT 0,
    error_message TEXT,
    metadata JSONB, -- Task-specific data
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Literature expansion history
CREATE TABLE IF NOT EXISTS expansions (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    topic TEXT,
    gap_analysis JSONB, -- Results from Knowledge Gap Analyzer (Agent 10)
    papers_found INT DEFAULT 0,
    papers_ingested INT DEFAULT 0,
    total_cost_usd DECIMAL(10,4) DEFAULT 0.0,
    task_id TEXT REFERENCES async_tasks(task_id),
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Search history for suggestions and analytics
CREATE TABLE IF NOT EXISTS search_history (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    query TEXT NOT NULL,
    mode TEXT CHECK (mode IN ('traditional', 'rag', 'kg')),
    results_count INT,
    filters JSONB, -- Filter criteria used
    created_at TIMESTAMP DEFAULT NOW()
);

-- Ingestion checkpoints for resume capability
CREATE TABLE IF NOT EXISTS ingestion_checkpoints (
    id SERIAL PRIMARY KEY,
    paper_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    checkpoint_name TEXT NOT NULL CHECK (checkpoint_name IN ('extracted', 'kg_updated', 'stored')),
    data JSONB, -- Checkpoint data for resume
    cost_usd DECIMAL(10,4) DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(paper_id, checkpoint_name)
);

-- Paper processing status tracking
CREATE TABLE IF NOT EXISTS paper_processing_status (
    paper_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'uploading', 'uploaded', 'ingesting', 'ingested', 'failed')),
    progress FLOAT DEFAULT 0.0 CHECK (progress >= 0 AND progress <= 1),
    details JSONB, -- Additional status details
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Storage tracking for files
CREATE TABLE IF NOT EXISTS paper_files (
    id SERIAL PRIMARY KEY,
    paper_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    file_type TEXT NOT NULL, -- pdf, docx, pptx, etc.
    file_path TEXT NOT NULL,
    file_size BIGINT,
    checksum TEXT, -- SHA256 hash
    uploaded_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(paper_id, file_type)
);

-- Indexes for performance optimization
CREATE INDEX IF NOT EXISTS idx_collections_user_id ON collections(user_id);
CREATE INDEX IF NOT EXISTS idx_collection_papers_collection_id ON collection_papers(collection_id);
CREATE INDEX IF NOT EXISTS idx_collection_papers_paper_id ON collection_papers(paper_id);
CREATE INDEX IF NOT EXISTS idx_paper_reading_status_user_id ON paper_reading_status(user_id);
CREATE INDEX IF NOT EXISTS idx_paper_reading_status_status ON paper_reading_status(status);
CREATE INDEX IF NOT EXISTS idx_paper_reading_status_starred ON paper_reading_status(starred);
CREATE INDEX IF NOT EXISTS idx_tags_user_id ON tags(user_id);
CREATE INDEX IF NOT EXISTS idx_paper_tags_paper_id ON paper_tags(paper_id);
CREATE INDEX IF NOT EXISTS idx_paper_tags_tag_id ON paper_tags(tag_id);
CREATE INDEX IF NOT EXISTS idx_async_tasks_user_id ON async_tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_async_tasks_status ON async_tasks(status);
CREATE INDEX IF NOT EXISTS idx_async_tasks_type_status ON async_tasks(task_type, status);
CREATE INDEX IF NOT EXISTS idx_expansions_user_id ON expansions(user_id);
CREATE INDEX IF NOT EXISTS idx_search_history_user_id ON search_history(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ingestion_checkpoints_paper_id ON ingestion_checkpoints(paper_id);
CREATE INDEX IF NOT EXISTS idx_paper_processing_status_user_id ON paper_processing_status(user_id);
CREATE INDEX IF NOT EXISTS idx_paper_files_paper_id ON paper_files(paper_id);

-- Views for common queries
CREATE OR REPLACE VIEW paper_stats_by_user AS
SELECT 
    user_id,
    COUNT(*) as total_papers,
    COUNT(*) FILTER (WHERE starred = true) as starred_papers,
    COUNT(*) FILTER (WHERE status = 'to_read') as to_read_papers,
    COUNT(*) FILTER (WHERE status = 'reading') as reading_papers,
    COUNT(*) FILTER (WHERE status = 'read') as read_papers
FROM paper_reading_status
GROUP BY user_id;

CREATE OR REPLACE VIEW collection_stats AS
SELECT 
    c.id,
    c.user_id,
    c.name,
    c.description,
    COUNT(cp.paper_id) as paper_count,
    c.created_at,
    c.updated_at
FROM collections c
LEFT JOIN collection_papers cp ON c.id = cp.collection_id
GROUP BY c.id, c.user_id, c.name, c.description, c.created_at, c.updated_at;

-- Comments for documentation
COMMENT ON TABLE collections IS 'User-defined collections for organizing papers';
COMMENT ON TABLE collection_papers IS 'Many-to-many relationship between collections and papers';
COMMENT ON TABLE paper_reading_status IS 'User reading status and interactions with papers';
COMMENT ON TABLE tags IS 'User-defined tags for categorizing papers';
COMMENT ON TABLE paper_tags IS 'Many-to-many relationship between papers and tags';
COMMENT ON TABLE async_tasks IS 'Tracking for long-running async operations';
COMMENT ON TABLE expansions IS 'History of literature expansion operations';
COMMENT ON TABLE search_history IS 'User search history for suggestions and analytics';
COMMENT ON TABLE ingestion_checkpoints IS 'Checkpoints for resumable ingestion process';
COMMENT ON TABLE paper_processing_status IS 'Real-time status of paper processing operations';
COMMENT ON TABLE paper_files IS 'File storage tracking for papers';