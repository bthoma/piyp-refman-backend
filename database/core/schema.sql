-- ============================================
-- PiyP Core Schema - User Profiles
-- ============================================
-- Uses Supabase auth.users for authentication
-- This schema only extends with user preferences

-- Create schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS core;

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- USERS & AUTHENTICATION
-- ============================================

-- Use Supabase Auth (auth.users table)
-- We just need profile/preferences

CREATE TABLE core.user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    full_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Preferences
    default_citation_style TEXT DEFAULT 'apa',
    timezone TEXT DEFAULT 'UTC',

    -- AI Features (user choices)
    ai_features_enabled BOOLEAN DEFAULT true,
    auto_ingest_uploads BOOLEAN DEFAULT false,  -- Auto-ingest PDFs (costs money)
    rag_search_enabled BOOLEAN DEFAULT true,
    kg_search_enabled BOOLEAN DEFAULT true,

    -- Subscription tier
    tier TEXT DEFAULT 'free' CHECK (tier IN ('free', 'basic', 'pro', 'enterprise')),

    -- Budget controls
    monthly_budget_usd DECIMAL(10,2) DEFAULT 10.00,
    current_month_spent_usd DECIMAL(10,2) DEFAULT 0.00,
    budget_alert_threshold DECIMAL(3,2) DEFAULT 0.80,  -- Alert at 80%

    CONSTRAINT valid_email CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$')
);

-- ============================================
-- RLS Policy for user_profiles
-- ============================================

ALTER TABLE core.user_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own profile"
    ON core.user_profiles FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
    ON core.user_profiles FOR UPDATE
    USING (auth.uid() = id);

-- ============================================
-- Functions & Triggers
-- ============================================

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION core.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_user_profiles_updated_at
    BEFORE UPDATE ON core.user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION core.update_updated_at_column();

-- ============================================
-- Grants
-- ============================================

-- Grant usage on schema
GRANT USAGE ON SCHEMA core TO anon, authenticated, service_role;

-- Grant appropriate permissions
GRANT SELECT ON ALL TABLES IN SCHEMA core TO anon;
GRANT ALL ON ALL TABLES IN SCHEMA core TO authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA core TO service_role;

-- Grant sequence permissions
GRANT USAGE ON ALL SEQUENCES IN SCHEMA core TO authenticated, service_role;
