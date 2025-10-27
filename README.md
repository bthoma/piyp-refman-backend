# PiyP Backend - Multi-Domain Architecture

**Professor in Your Pocket (PiyP)** - AI-powered research and teaching platform with domain-driven architecture.

## 🏗️ Architecture Overview

PiyP uses a **multi-database, domain-driven architecture** with clear separation of concerns:

### Databases

1. **Core DB** (`piyp-core`): Authentication and user management
2. **RefMan DB** (`piyp-refman`): Reference manager domain
3. **Research DB** (`piyp-research`): Research agents (future)
4. **Teaching DB** (`piyp-teaching`): Course generation (future)

### Project Structure

```
piyp-backend/
├── config/              # Configuration management
│   ├── database.py      # Multi-database Supabase clients
│   └── settings.py      # Application settings
├── database/            # SQL schema files
│   ├── core/            # Core DB schemas
│   └── refman/          # RefMan DB schemas
├── domains/             # Domain-driven modules
│   ├── core/            # Auth domain
│   └── refman/          # Reference manager domain
├── mcp_tools/           # MCP tool implementations
├── tests/               # Test suites
└── main.py              # FastAPI application entry
```

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Two Supabase projects (Core and RefMan)
- Virtual environment (recommended)

### Setup

1. **Clone and navigate:**
   ```bash
   cd piyp-backend
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your Supabase credentials
   ```

5. **Deploy database schemas:**
   ```bash
   # Core DB schema
   # Run database/core/schema.sql in your Core Supabase project
   
   # RefMan DB schema
   # Run database/refman/schema.sql in your RefMan Supabase project
   ```

## 🎯 Development Phases

### Phase 1: Core Auth Domain ✅
- User authentication and authorization
- JWT token management
- User profiles and preferences
- Web interface with iOS app in mind

### Phase 2: Reference Manager Domain 🔄
- Paper upload and management
- Collections and tags
- Traditional, RAG, and HippoRAG search
- PDF viewing and annotations
- Citation export (BibTeX, RIS, etc.)
- Complete reference management workflow

### Phase 3: Research Agents (Future)
- Autonomous paper discovery
- PDF recovery
- Gap analysis
- Literature review generation

## 🔐 Environment Variables

See `.env.example` for all required configuration. Key variables:

```bash
# Supabase Core (Auth)
CORE_SUPABASE_URL=https://[project-id].supabase.co
CORE_SUPABASE_ANON_KEY=eyJ...
CORE_SUPABASE_SERVICE_KEY=eyJ...

# Supabase RefMan
REFMAN_SUPABASE_URL=https://[project-id].supabase.co
REFMAN_SUPABASE_ANON_KEY=eyJ...
REFMAN_SUPABASE_SERVICE_KEY=eyJ...
```

## 📚 Documentation

- [Schema Design](/database/README.md)
- [API Documentation](docs/API.md) (coming soon)
- [MCP Tools](docs/MCP_TOOLS.md) (coming soon)

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=domains --cov-report=html

# Run specific domain tests
pytest tests/test_core/
pytest tests/test_refman/
```

## 🛠️ Development

```bash
# Run development server
uvicorn main:app --reload --port 8000

# Format code
black .

# Lint
flake8

# Type check
mypy .
```

## 📝 Database Management

### Core Database
```bash
# Deploy schema
psql [connection-string] < database/core/schema.sql

# Verify
psql [connection-string] -c "\dt"
```

### RefMan Database
```bash
# Deploy schema
psql [connection-string] < database/refman/schema.sql

# Verify
psql [connection-string] -c "\dt"
```

## 🤝 Contributing

This is a research project. See planning docs in `/docs` for architectural decisions and roadmap.

## 📄 License

[To be determined]

## 🔗 Related Projects

- Planning docs: `/Users/brentthoma/Dropbox/PiyP/docs/`
- iOS app: (future)
- Frontend: (future)

---

**Built with:** FastAPI, Supabase, Python 3.11+
