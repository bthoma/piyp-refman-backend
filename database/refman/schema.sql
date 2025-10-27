-- ============================================
-- PiyP RefMan Schema - Reference Manager
-- ============================================
-- AI-enhanced reference management system
-- All tables reference auth.users(id) from Supabase

-- Create schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS refman;

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ============================================
-- PAPERS - Core reference library
-- ============================================

CREATE TABLE refman.papers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- External identifiers (for deduplication)
    paper_id TEXT,  -- External ID (DOI, ArXiv, PMID, etc.)
    doi TEXT,
    arxiv_id TEXT,
    pmid TEXT,
    pmc_id TEXT,

    -- Core metadata
    title TEXT NOT NULL,
    authors TEXT[] NOT NULL DEFAULT '{}',
    abstract TEXT,
    publication_year INTEGER,
    publication_date DATE,
    venue TEXT,  -- Journal, conference, etc.
    volume TEXT,
    issue TEXT,
    pages TEXT,
    publisher TEXT,

    -- URLs and files
    url TEXT,
    pdf_url TEXT,
    pdf_path TEXT,  -- Local storage path
    pdf_size_bytes BIGINT,
    pdf_checksum TEXT,

    -- Citation info
    citation_count INTEGER DEFAULT 0,
    influential_citation_count INTEGER DEFAULT 0,

    -- Classification
    fields_of_study TEXT[],
    keywords TEXT[],

    -- Paper source tracking
    source_type TEXT NOT NULL DEFAULT 'upload'
        CHECK (source_type IN ('upload', 'research', 'import', 'autonomous', 'manual')),
    source_metadata JSONB,  -- Source-specific data

    -- AI processing status
    ingestion_status TEXT DEFAULT 'not_ingested'
        CHECK (ingestion_status IN ('not_ingested', 'pending', 'processing', 'ingested', 'failed')),
    ingestion_cost_usd DECIMAL(10,4),
    ingested_at TIMESTAMP WITH TIME ZONE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT papers_unique_user_paper_id UNIQUE (user_id, paper_id),
    CONSTRAINT papers_unique_user_doi UNIQUE (user_id, doi) WHERE doi IS NOT NULL,
    CONSTRAINT valid_year CHECK (publication_year IS NULL OR
        (publication_year >= 1000 AND publication_year <= EXTRACT(YEAR FROM NOW()) + 1))
);

-- Indexes for performance
CREATE INDEX idx_papers_user_id ON refman.papers(user_id);
CREATE INDEX idx_papers_paper_id ON refman.papers(paper_id) WHERE paper_id IS NOT NULL;
CREATE INDEX idx_papers_doi ON refman.papers(doi) WHERE doi IS NOT NULL;
CREATE INDEX idx_papers_arxiv_id ON refman.papers(arxiv_id) WHERE arxiv_id IS NOT NULL;
CREATE INDEX idx_papers_title ON refman.papers USING gin(to_tsvector('english', title));
CREATE INDEX idx_papers_abstract ON refman.papers USING gin(to_tsvector('english', abstract)) WHERE abstract IS NOT NULL;
CREATE INDEX idx_papers_authors ON refman.papers USING gin(authors);
CREATE INDEX idx_papers_year ON refman.papers(publication_year) WHERE publication_year IS NOT NULL;
CREATE INDEX idx_papers_source_type ON refman.papers(source_type);
CREATE INDEX idx_papers_ingestion_status ON refman.papers(ingestion_status);
CREATE INDEX idx_papers_created_at ON refman.papers(created_at DESC);

-- RLS Policies
ALTER TABLE refman.papers ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own papers"
    ON refman.papers FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own papers"
    ON refman.papers FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own papers"
    ON refman.papers FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own papers"
    ON refman.papers FOR DELETE
    USING (auth.uid() = user_id);

-- Trigger for updated_at
CREATE TRIGGER update_papers_updated_at
    BEFORE UPDATE ON refman.papers
    FOR EACH ROW
    EXECUTE FUNCTION core.update_updated_at_column();

-- ============================================
-- COLLECTIONS - User-organized paper groups
-- ============================================

CREATE TABLE refman.collections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    name TEXT NOT NULL,
    description TEXT,
    color TEXT,  -- Hex color for UI
    icon TEXT,   -- Icon name for UI

    -- Collection type
    is_smart BOOLEAN DEFAULT false,  -- Smart collections with rules
    smart_rules JSONB,  -- Rules for auto-population

    -- Ordering
    sort_order INTEGER DEFAULT 0,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT collections_unique_user_name UNIQUE (user_id, name)
);

CREATE INDEX idx_collections_user_id ON refman.collections(user_id);
CREATE INDEX idx_collections_sort_order ON refman.collections(user_id, sort_order);

-- RLS Policies
ALTER TABLE refman.collections ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own collections"
    ON refman.collections FOR ALL
    USING (auth.uid() = user_id);

-- Trigger
CREATE TRIGGER update_collections_updated_at
    BEFORE UPDATE ON refman.collections
    FOR EACH ROW
    EXECUTE FUNCTION core.update_updated_at_column();

-- ============================================
-- COLLECTION_PAPERS - Many-to-many
-- ============================================

CREATE TABLE refman.collection_papers (
    collection_id UUID REFERENCES refman.collections(id) ON DELETE CASCADE,
    paper_id UUID REFERENCES refman.papers(id) ON DELETE CASCADE,

    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    sort_order INTEGER DEFAULT 0,  -- Manual ordering within collection

    PRIMARY KEY (collection_id, paper_id)
);

CREATE INDEX idx_collection_papers_collection_id ON refman.collection_papers(collection_id);
CREATE INDEX idx_collection_papers_paper_id ON refman.collection_papers(paper_id);
CREATE INDEX idx_collection_papers_sort_order ON refman.collection_papers(collection_id, sort_order);

-- RLS Policy - papers can only be added to user's own collections
ALTER TABLE refman.collection_papers ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage papers in own collections"
    ON refman.collection_papers FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM refman.collections
            WHERE refman.collections.id = refman.collection_papers.collection_id
            AND refman.collections.user_id = auth.uid()
        )
    );

-- ============================================
-- TAGS - User-defined labels
-- ============================================

CREATE TABLE refman.tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    name TEXT NOT NULL,
    color TEXT,  -- Hex color

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT tags_unique_user_name UNIQUE (user_id, name)
);

CREATE INDEX idx_tags_user_id ON refman.tags(user_id);
CREATE INDEX idx_tags_name ON refman.tags(user_id, name);

-- RLS
ALTER TABLE refman.tags ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own tags"
    ON refman.tags FOR ALL
    USING (auth.uid() = user_id);

-- ============================================
-- PAPER_TAGS - Many-to-many
-- ============================================

CREATE TABLE refman.paper_tags (
    paper_id UUID REFERENCES refman.papers(id) ON DELETE CASCADE,
    tag_id UUID REFERENCES refman.tags(id) ON DELETE CASCADE,

    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    PRIMARY KEY (paper_id, tag_id)
);

CREATE INDEX idx_paper_tags_paper_id ON refman.paper_tags(paper_id);
CREATE INDEX idx_paper_tags_tag_id ON refman.paper_tags(tag_id);

-- RLS
ALTER TABLE refman.paper_tags ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage tags on own papers"
    ON refman.paper_tags FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM refman.papers
            WHERE refman.papers.id = refman.paper_tags.paper_id
            AND refman.papers.user_id = auth.uid()
        )
    );

-- ============================================
-- READING_STATUS - User's reading progress
-- ============================================

CREATE TABLE refman.reading_status (
    paper_id UUID PRIMARY KEY REFERENCES refman.papers(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Status tracking
    status TEXT DEFAULT 'to_read'
        CHECK (status IN ('to_read', 'reading', 'read', 'skimmed', 'abandoned')),

    -- User rating and importance
    starred BOOLEAN DEFAULT false,
    rating INTEGER CHECK (rating IS NULL OR (rating >= 1 AND rating <= 5)),
    priority INTEGER CHECK (priority IS NULL OR (priority >= 1 AND priority <= 5)),

    -- Reading progress
    pages_read INTEGER,
    reading_progress DECIMAL(3,2) CHECK (reading_progress IS NULL OR
        (reading_progress >= 0 AND reading_progress <= 1)),

    -- Timestamps
    started_reading_at TIMESTAMP WITH TIME ZONE,
    completed_reading_at TIMESTAMP WITH TIME ZONE,
    last_accessed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT reading_status_user_paper UNIQUE (user_id, paper_id)
);

CREATE INDEX idx_reading_status_user_id ON refman.reading_status(user_id);
CREATE INDEX idx_reading_status_status ON refman.reading_status(user_id, status);
CREATE INDEX idx_reading_status_starred ON refman.reading_status(user_id, starred) WHERE starred = true;
CREATE INDEX idx_reading_status_last_accessed ON refman.reading_status(user_id, last_accessed_at DESC);

-- RLS
ALTER TABLE refman.reading_status ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own reading status"
    ON refman.reading_status FOR ALL
    USING (auth.uid() = user_id);

-- Trigger
CREATE TRIGGER update_reading_status_updated_at
    BEFORE UPDATE ON refman.reading_status
    FOR EACH ROW
    EXECUTE FUNCTION core.update_updated_at_column();

-- ============================================
-- NOTES - User annotations and highlights
-- ============================================

CREATE TABLE refman.notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paper_id UUID NOT NULL REFERENCES refman.papers(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Note content
    note_type TEXT DEFAULT 'general'
        CHECK (note_type IN ('general', 'summary', 'methodology', 'results',
                             'critique', 'idea', 'question', 'highlight')),
    content TEXT NOT NULL,

    -- Location in paper
    page_number INTEGER,
    highlight_text TEXT,  -- Original text that was highlighted
    location_metadata JSONB,  -- PDF coordinates, etc.

    -- Organization
    is_private BOOLEAN DEFAULT true,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_notes_paper_id ON refman.notes(paper_id);
CREATE INDEX idx_notes_user_id ON refman.notes(user_id);
CREATE INDEX idx_notes_type ON refman.notes(user_id, note_type);
CREATE INDEX idx_notes_created_at ON refman.notes(user_id, created_at DESC);
CREATE INDEX idx_notes_content ON refman.notes USING gin(to_tsvector('english', content));

-- RLS
ALTER TABLE refman.notes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own notes"
    ON refman.notes FOR ALL
    USING (auth.uid() = user_id);

-- Trigger
CREATE TRIGGER update_notes_updated_at
    BEFORE UPDATE ON refman.notes
    FOR EACH ROW
    EXECUTE FUNCTION core.update_updated_at_column();

-- ============================================
-- INGESTION_JOBS - Track AI processing
-- ============================================

CREATE TABLE refman.ingestion_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paper_id UUID NOT NULL REFERENCES refman.papers(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Job status
    status TEXT DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')),

    -- Processing stages with checkpoints
    stage TEXT DEFAULT 'queued'
        CHECK (stage IN ('queued', 'extracting', 'extracted', 'embedding',
                        'embedded', 'kg_building', 'kg_built', 'complete')),

    checkpoint_data JSONB,  -- Save progress for resume

    -- Progress tracking
    progress DECIMAL(3,2) DEFAULT 0.00
        CHECK (progress >= 0 AND progress <= 1),

    -- Results
    extracted_text_length INTEGER,
    entities_extracted INTEGER,
    relationships_created INTEGER,
    chunks_created INTEGER,

    -- Cost tracking
    estimated_cost_usd DECIMAL(10,4),
    actual_cost_usd DECIMAL(10,4),

    -- Error handling
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,

    -- Timestamps
    queued_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    failed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_ingestion_jobs_paper_id ON refman.ingestion_jobs(paper_id);
CREATE INDEX idx_ingestion_jobs_user_id ON refman.ingestion_jobs(user_id);
CREATE INDEX idx_ingestion_jobs_status ON refman.ingestion_jobs(status) WHERE status IN ('pending', 'processing');
CREATE INDEX idx_ingestion_jobs_queued_at ON refman.ingestion_jobs(queued_at) WHERE status = 'pending';

-- RLS
ALTER TABLE refman.ingestion_jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own ingestion jobs"
    ON refman.ingestion_jobs FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can cancel own ingestion jobs"
    ON refman.ingestion_jobs FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- ============================================
-- RESEARCH_PAPER_LINKS - Bridge to research_papers table
-- ============================================

CREATE TABLE refman.research_paper_links (
    paper_id UUID NOT NULL REFERENCES refman.papers(id) ON DELETE CASCADE,
    research_paper_id UUID,  -- References research_papers(id) in old schema
    research_query_id UUID,  -- References research_queries(id) in old schema

    link_type TEXT NOT NULL
        CHECK (link_type IN ('discovered', 'promoted', 'imported')),

    link_metadata JSONB,  -- Context about how/why linked

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    PRIMARY KEY (paper_id, research_paper_id)
);

CREATE INDEX idx_research_links_paper_id ON refman.research_paper_links(paper_id);
CREATE INDEX idx_research_links_research_paper_id ON refman.research_paper_links(research_paper_id);
CREATE INDEX idx_research_links_research_query_id ON refman.research_paper_links(research_query_id);

-- RLS
ALTER TABLE refman.research_paper_links ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view links for own papers"
    ON refman.research_paper_links FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM refman.papers
            WHERE refman.papers.id = refman.research_paper_links.paper_id
            AND refman.papers.user_id = auth.uid()
        )
    );

-- ============================================
-- SEARCH_HISTORY - Track searches for suggestions
-- ============================================

CREATE TABLE refman.search_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    query TEXT NOT NULL,
    search_mode TEXT NOT NULL
        CHECK (search_mode IN ('traditional', 'rag', 'kg')),

    filters JSONB,  -- Applied filters
    results_count INTEGER,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_search_history_user_id ON refman.search_history(user_id, created_at DESC);
CREATE INDEX idx_search_history_query ON refman.search_history USING gin(to_tsvector('english', query));

-- RLS
ALTER TABLE refman.search_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own search history"
    ON refman.search_history FOR ALL
    USING (auth.uid() = user_id);

-- Auto-cleanup old searches (keep last 1000 per user)
CREATE OR REPLACE FUNCTION refman.cleanup_old_search_history()
RETURNS TRIGGER AS $$
BEGIN
    DELETE FROM refman.search_history
    WHERE user_id = NEW.user_id
    AND id NOT IN (
        SELECT id FROM refman.search_history
        WHERE user_id = NEW.user_id
        ORDER BY created_at DESC
        LIMIT 1000
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER cleanup_search_history_trigger
    AFTER INSERT ON refman.search_history
    FOR EACH ROW
    EXECUTE FUNCTION refman.cleanup_old_search_history();

-- ============================================
-- CITATION_EXPORTS - Track citation exports
-- ============================================

CREATE TABLE refman.citation_exports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    export_type TEXT NOT NULL
        CHECK (export_type IN ('bibtex', 'ris', 'endnote', 'zotero', 'bibliography')),

    citation_style TEXT NOT NULL,  -- apa, mla, chicago, etc.
    paper_ids UUID[] NOT NULL,

    file_path TEXT,  -- If exported to file
    file_size_bytes BIGINT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_citation_exports_user_id ON refman.citation_exports(user_id, created_at DESC);

-- RLS
ALTER TABLE refman.citation_exports ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own citation exports"
    ON refman.citation_exports FOR ALL
    USING (auth.uid() = user_id);

-- ============================================
-- USER_ACTIVITY_LOG - Track user actions
-- ============================================

CREATE TABLE refman.user_activity_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    activity_type TEXT NOT NULL
        CHECK (activity_type IN ('paper_added', 'paper_viewed', 'paper_read',
                                 'search', 'export', 'ingestion', 'collection_created')),

    entity_type TEXT,  -- paper, collection, tag, etc.
    entity_id UUID,

    metadata JSONB,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_activity_log_user_id ON refman.user_activity_log(user_id, created_at DESC);
CREATE INDEX idx_activity_log_type ON refman.user_activity_log(user_id, activity_type, created_at DESC);

-- RLS
ALTER TABLE refman.user_activity_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own activity"
    ON refman.user_activity_log FOR SELECT
    USING (auth.uid() = user_id);

-- Auto-cleanup old activity (keep last 10000 per user)
CREATE OR REPLACE FUNCTION refman.cleanup_old_activity_log()
RETURNS TRIGGER AS $$
BEGIN
    DELETE FROM refman.user_activity_log
    WHERE user_id = NEW.user_id
    AND id NOT IN (
        SELECT id FROM refman.user_activity_log
        WHERE user_id = NEW.user_id
        ORDER BY created_at DESC
        LIMIT 10000
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER cleanup_activity_log_trigger
    AFTER INSERT ON refman.user_activity_log
    FOR EACH ROW
    EXECUTE FUNCTION refman.cleanup_old_activity_log();

-- ============================================
-- VIEWS - Pre-computed queries for performance
-- ============================================

-- User statistics
CREATE OR REPLACE VIEW refman.user_stats AS
SELECT
    p.user_id,
    COUNT(DISTINCT p.id) as total_papers,
    COUNT(DISTINCT CASE WHEN p.ingestion_status = 'ingested' THEN p.id END) as ingested_papers,
    COUNT(DISTINCT CASE WHEN rs.starred = true THEN p.id END) as starred_papers,
    COUNT(DISTINCT CASE WHEN rs.status = 'to_read' THEN p.id END) as to_read_papers,
    COUNT(DISTINCT CASE WHEN rs.status = 'reading' THEN p.id END) as reading_papers,
    COUNT(DISTINCT CASE WHEN rs.status = 'read' THEN p.id END) as read_papers,
    COUNT(DISTINCT c.id) as collections_count,
    COUNT(DISTINCT t.id) as tags_count,
    COALESCE(SUM(p.ingestion_cost_usd), 0) as total_ingestion_cost,
    MAX(p.created_at) as last_paper_added,
    MAX(rs.last_accessed_at) as last_activity
FROM refman.papers p
LEFT JOIN refman.reading_status rs ON p.id = rs.paper_id
LEFT JOIN refman.paper_tags pt ON p.id = pt.paper_id
LEFT JOIN refman.tags t ON pt.tag_id = t.id AND t.user_id = p.user_id
LEFT JOIN refman.collection_papers cp ON p.id = cp.paper_id
LEFT JOIN refman.collections c ON cp.collection_id = c.id AND c.user_id = p.user_id
GROUP BY p.user_id;

-- Collection statistics
CREATE OR REPLACE VIEW refman.collection_stats AS
SELECT
    c.id as collection_id,
    c.user_id,
    c.name,
    c.description,
    c.color,
    COUNT(cp.paper_id) as paper_count,
    MAX(cp.added_at) as last_paper_added
FROM refman.collections c
LEFT JOIN refman.collection_papers cp ON c.id = cp.collection_id
GROUP BY c.id, c.user_id, c.name, c.description, c.color;

-- Tag usage statistics
CREATE OR REPLACE VIEW refman.tag_stats AS
SELECT
    t.id as tag_id,
    t.user_id,
    t.name,
    t.color,
    COUNT(pt.paper_id) as paper_count,
    MAX(pt.added_at) as last_used
FROM refman.tags t
LEFT JOIN refman.paper_tags pt ON t.id = pt.tag_id
GROUP BY t.id, t.user_id, t.name, t.color;

-- Recent papers with reading status
CREATE OR REPLACE VIEW refman.recent_papers AS
SELECT
    p.*,
    rs.status,
    rs.starred,
    rs.rating,
    rs.last_accessed_at,
    ARRAY_AGG(DISTINCT t.name) FILTER (WHERE t.name IS NOT NULL) as tag_names,
    ARRAY_AGG(DISTINCT c.name) FILTER (WHERE c.name IS NOT NULL) as collection_names
FROM refman.papers p
LEFT JOIN refman.reading_status rs ON p.id = rs.paper_id
LEFT JOIN refman.paper_tags pt ON p.id = pt.paper_id
LEFT JOIN refman.tags t ON pt.tag_id = t.id
LEFT JOIN refman.collection_papers cp ON p.id = cp.paper_id
LEFT JOIN refman.collections c ON cp.collection_id = c.id
GROUP BY p.id, rs.status, rs.starred, rs.rating, rs.last_accessed_at
ORDER BY p.created_at DESC;

-- ============================================
-- Grants
-- ============================================

-- Grant usage on schema
GRANT USAGE ON SCHEMA refman TO anon, authenticated, service_role;

-- Grant appropriate permissions
GRANT SELECT ON ALL TABLES IN SCHEMA refman TO anon;
GRANT ALL ON ALL TABLES IN SCHEMA refman TO authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA refman TO service_role;

-- Grant sequence permissions
GRANT USAGE ON ALL SEQUENCES IN SCHEMA refman TO authenticated, service_role;
