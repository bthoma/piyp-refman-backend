# PiyP Database Schema Documentation

## Overview

PiyP uses a single Supabase database with multiple schemas to organize different domains:

- **core**: Authentication, users, and shared functionality
- **refman**: Reference manager domain
- **research**: Research agents (future)
- **teaching**: Course generation (future)

## Schema Deployment

### Prerequisites

1. Create a single Supabase project
2. Get your database connection string from Supabase dashboard

### Deploy Schemas

Deploy each schema SQL file to your Supabase database:

```bash
# Using Supabase CLI
supabase db push --db-url "postgresql://[connection-string]" < database/core/schema.sql
supabase db push --db-url "postgresql://[connection-string]" < database/refman/schema.sql

# Or using psql
psql [connection-string] < database/core/schema.sql
psql [connection-string] < database/refman/schema.sql
```

### Verify Deployment

```sql
-- List schemas
SELECT schema_name FROM information_schema.schemata 
WHERE schema_name IN ('core', 'refman');

-- List tables in core schema
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'core';

-- List tables in refman schema
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'refman';
```

## Core Schema

The core schema handles authentication and user management:

- **users**: User accounts and profiles
- **roles**: User roles (user, premium, admin)
- **user_roles**: User-role assignments
- **api_keys**: API key management
- **sessions**: Refresh token sessions
- **audit_logs**: User action logging

## RefMan Schema

The reference manager schema handles paper organization:

- **papers**: Academic papers and metadata
- **collections**: Paper organization
- **paper_collections**: Paper-collection relationships
- **annotations**: PDF annotations
- **citations**: Citation formats
- **reading_sessions**: Reading progress tracking
- **import_history**: Import job tracking
- **shared_libraries**: Collection sharing

## Security

All tables have Row Level Security (RLS) enabled. Users can only access their own data.

## Migrations

Future schema changes should be added as migration files in:
- `database/migrations/core/`
- `database/migrations/refman/`

## Vector Search

RefMan papers table includes vector columns for semantic search:
- `title_vector`: Title embeddings (1536 dimensions)
- `abstract_vector`: Abstract embeddings (1536 dimensions)

Ensure the `vector` extension is enabled in your Supabase project.