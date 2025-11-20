# CaseMind - Legal Case Similarity Search System

## Overview
CaseMind is a sophisticated legal case similarity search system built with Haystack, PostgreSQL+pgvector, and advanced NLP models. It enables semantic search, duplicate detection, and batch processing of legal documents.

## Architecture

### Design Principles
- **SOLID Principles**: Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion
- **Design Patterns**: Singleton, Factory, Adapter, Strategy, Facade
- **Clean Architecture**: Core → Infrastructure → Services → Pipelines → Presentation

### Key Features
- ✅ Dual embedding architecture (facts + metadata)
- ✅ Batch processing with duplicate detection
- ✅ Cross-encoder re-ranking with threshold filtering
- ✅ PostgreSQL + pgvector for efficient similarity search
- ✅ Template-based fact extraction using LLMs
- ✅ Rich CLI interface with progress tracking

## System Requirements

### Software Dependencies
- Python 3.9+
- PostgreSQL 14+ with pgvector extension
- 4GB+ RAM (8GB recommended for large batches)
- 10GB+ disk space for models and database

### Python Packages
See `requirements.txt` for complete list. Key dependencies:
- `haystack-ai` - Pipeline framework
- `sentence-transformers` - Embedding models
- `transformers` - Cross-encoder models
- `psycopg2-binary` - PostgreSQL adapter
- `PyMuPDF` - PDF processing
- `rich` - CLI interface
- `python-dotenv` - Configuration management

## Installation

### 1. Install PostgreSQL + pgvector

#### Windows (using PostgreSQL installer)
1. Download PostgreSQL 14+ from https://www.postgresql.org/download/windows/
2. Run installer and note down:
   - PostgreSQL port (default: 5432)
   - Superuser password
   - Installation directory

3. Install pgvector extension:
   ```powershell
   # Download pgvector for Windows from: https://github.com/pgvector/pgvector/releases
   # Extract and copy .dll files to PostgreSQL's lib directory
   # Copy .sql files to share/extension directory
   ```

4. Enable pgvector:
   ```powershell
   # Connect to PostgreSQL
   psql -U postgres
   
   # Create database
   CREATE DATABASE casemind;
   
   # Connect to casemind database
   \c casemind
   
   # Enable pgvector extension
   CREATE EXTENSION vector;
   
   # Verify installation
   SELECT * FROM pg_extension WHERE extname = 'vector';
   ```

#### Alternative: Using Docker
```powershell
# Run PostgreSQL with pgvector
docker run --name casemind-postgres `
  -e POSTGRES_PASSWORD=yourpassword `
  -e POSTGRES_DB=casemind `
  -p 5432:5432 `
  -d pgvector/pgvector:pg14

# Verify
docker exec -it casemind-postgres psql -U postgres -d casemind -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 2. Clone Repository
```powershell
git clone https://github.com/G2703/CaseMind.git
cd CaseMind
git checkout dev-haystack
```

### 3. Create Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1

# If you encounter execution policy error:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 4. Install Python Dependencies
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Configure Environment
Create `.env` file in project root:

```env
# Database Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=casemind
POSTGRES_USER=postgres
POSTGRES_PASSWORD=yourpassword

# Model Configuration
EMBEDDING_MODEL=sentence-transformers/all-mpnet-base-v2
RANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2

# Pipeline Configuration
TOP_K_SIMILAR_CASES=3
CROSS_ENCODER_THRESHOLD=0.0

# OpenAI API Key (for metadata/fact extraction)
OPENAI_API_KEY=your_openai_api_key_here

# Paths
ONTOLOGY_PATH=Ontology_schema/ontology_schema.json
TEMPLATES_DIR=templates
CASES_DIR=cases

# Logging
LOG_LEVEL=INFO
DISABLE_LOGGING=false
```

### 6. Initialize Database
```powershell
# Run initialization script
python -m src.scripts.init_database
```

This will:
- Check PostgreSQL connection
- Ensure pgvector extension is installed
- Create database schema with tables and indexes
- Verify setup

## Usage

### Starting the Application
```powershell
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Run CLI application
python -m src.main
```

### Main Menu Options

#### 1. **Ingest Cases (Batch)**
Build the database by processing a folder of PDF cases:

```
Select option: 1
Enter folder path: C:\path\to\cases\input_files
```

Features:
- Processes all PDFs in folder
- Automatic duplicate detection (skips already-stored cases)
- Progress tracking with Rich UI
- Error handling per file

#### 2. **Find Similar Cases**
Search for similar cases given an input PDF:

```
Select option: 2
Enter PDF file path: C:\path\to\case.pdf
```

Output:
- Input case summary with metadata
- Top-K similar cases ranked by relevance
- Cosine similarity + cross-encoder scores
- Filtered by threshold

#### 3. **Database Statistics**
View database information:
```
Select option: 3
```

Shows:
- Total documents stored
- Unique templates
- Date range of cases
- Storage statistics

#### 4. **Health Check**
Verify system status:
```
Select option: 4
```

Checks:
- PostgreSQL connection
- pgvector extension
- Embedding model availability
- Ranker model availability

### Batch Processing Example

```
╔════════════════════════════════════════════════════════════╗
║            BATCH INGESTION: Building Database              ║
╠════════════════════════════════════════════════════════════╣
║ Folder: C:\Cases\input_files                              ║
║ Total PDFs: 150                                            ║
╠════════════════════════════════════════════════════════════╣
║ Progress: ████████████████░░░░░░░░░░  65% (98/150)        ║
║                                                            ║
║ ✓ Processed:  85                                           ║
║ ⊘ Duplicates: 13                                           ║
║ ✗ Failed:     0                                            ║
║                                                            ║
║ Current: Processing "Abdul_Karim_vs_State.pdf"            ║
╚════════════════════════════════════════════════════════════╝
```

### Similarity Search Example

```
╔════════════════════════════════════════════════════════════╗
║              FINDING SIMILAR CASES                         ║
╠════════════════════════════════════════════════════════════╣
║ Input File: Aakash_Chavan_vs_State.pdf                    ║
╠════════════════════════════════════════════════════════════╣
║ Phase 1: Processing Input Case                            ║
║   ✓ PDF loaded                                             ║
║   ✓ Metadata extracted                                     ║
║   ✓ Template: IPC 302 (Murder Case)                        ║
║   ✓ Facts extracted                                        ║
║   ✓ Embedding computed                                     ║
║   ✓ Stored in database                                     ║
╠════════════════════════════════════════════════════════════╣
║ Phase 2: Searching Similar Cases                          ║
║   ✓ Found 2 cases above threshold (0.0)                   ║
╠════════════════════════════════════════════════════════════╣
║ RESULTS: 2 Similar Cases Found                            ║
║ ┌────────────────────────────────────────────────────────┐ ║
║ │ 1. Abdul Karim Vs State of Karnataka                  │ ║
║ │    Cosine Similarity: 0.87 | Cross-Encoder: 0.82      │ ║
║ │    Court: High Court Karnataka | Date: 2023-05-10     │ ║
║ │    Summary: Murder case involving knife attack...     │ ║
║ └────────────────────────────────────────────────────────┘ ║
╚════════════════════════════════════════════════════════════╝
```

## Project Structure

```
CaseMind/
├── src/
│   ├── core/                    # Core abstractions and interfaces
│   │   ├── __init__.py
│   │   ├── config.py           # Singleton configuration
│   │   ├── exceptions.py       # Custom exceptions
│   │   ├── interfaces.py       # Abstract base classes
│   │   └── models.py           # Data models (dataclasses)
│   │
│   ├── infrastructure/         # External integrations
│   │   ├── __init__.py
│   │   └── document_store.py  # PostgreSQL + pgvector
│   │
│   ├── services/              # Business logic services
│   │   ├── __init__.py
│   │   ├── pdf_loader.py      # PDF loading (Adapter pattern)
│   │   ├── embedding_service.py # Dual embeddings
│   │   ├── metadata_extractor.py # LLM-based extraction
│   │   ├── template_selector.py # Template matching
│   │   ├── fact_extractor.py  # Fact extraction
│   │   └── duplicate_checker.py # Duplicate detection
│   │
│   ├── pipelines/             # Haystack pipeline orchestrators
│   │   ├── __init__.py
│   │   ├── ingestion_pipeline.py # Data ingestion
│   │   └── similarity_pipeline.py # Search pipeline
│   │
│   ├── presentation/          # UI and formatting
│   │   ├── __init__.py
│   │   ├── cli_app.py         # Main CLI application
│   │   └── formatters.py      # Rich UI formatters
│   │
│   ├── utils/                 # Utility functions
│   │   ├── __init__.py
│   │   └── helpers.py         # Helper functions
│   │
│   ├── scripts/               # Utility scripts
│   │   ├── __init__.py
│   │   └── init_database.py   # Database initialization
│   │
│   └── main.py                # Application entry point
│
├── tests/                     # Unit and integration tests
├── Ontology_schema/          # Legal ontology schemas
├── templates/                # Fact extraction templates
├── cases/                    # Legal case documents
├── config.json               # Application configuration
├── .env                      # Environment variables
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_HOST` | PostgreSQL hostname | `localhost` |
| `POSTGRES_PORT` | PostgreSQL port | `5432` |
| `POSTGRES_DB` | Database name | `casemind` |
| `POSTGRES_USER` | Database user | `postgres` |
| `POSTGRES_PASSWORD` | Database password | `password` |
| `EMBEDDING_MODEL` | Sentence-transformers model | `sentence-transformers/all-mpnet-base-v2` |
| `RANKER_MODEL` | Cross-encoder model | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| `TOP_K_SIMILAR_CASES` | Number of similar cases to retrieve | `3` |
| `CROSS_ENCODER_THRESHOLD` | Minimum score for results | `0.0` |
| `OPENAI_API_KEY` | OpenAI API key for LLM extraction | Required |
| `LOG_LEVEL` | Logging level | `INFO` |

### config.json

Optional configuration file for additional settings:
```json
{
  "openai_api_key": "your_key_here",
  "ontology_path": "Ontology_schema/ontology_schema.json",
  "templates_dir": "templates",
  "cases_dir": "cases"
}
```

## Database Schema

### Table: `haystack_documents`

| Column | Type | Description |
|--------|------|-------------|
| `id` | VARCHAR(255) PK | Unique document identifier |
| `content` | TEXT | Facts summary text |
| `content_type` | VARCHAR(50) | Content type (default: 'text') |
| `meta` | JSONB | Complete case metadata |
| `embedding_facts` | vector(768) | Facts embedding for similarity |
| `embedding_metadata` | vector(768) | Metadata embedding for entity search |
| `score` | FLOAT | Query result score (nullable) |
| `file_hash` | VARCHAR(64) UNIQUE | SHA-256 file hash |
| `original_filename` | VARCHAR(512) | Original PDF filename |
| `created_at` | TIMESTAMP | Creation timestamp |
| `updated_at` | TIMESTAMP | Last update timestamp |

### Indexes
- IVFFlat vector indexes on both embeddings
- GIN index on JSONB metadata
- B-tree indexes on case_id, file_hash, template_id, case_title

## Troubleshooting

### Database Connection Issues
```powershell
# Test PostgreSQL connection
psql -U postgres -h localhost -p 5432 -d casemind

# Check if database exists
psql -U postgres -c "\l"

# Check if pgvector is installed
psql -U postgres -d casemind -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

### Model Download Issues
Models are downloaded automatically on first use. If you have network issues:
```powershell
# Pre-download models
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-mpnet-base-v2')"
python -c "from sentence_transformers import CrossEncoder; CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"
```

### Memory Issues
For large batch processing:
- Reduce batch size in code
- Increase system RAM
- Use cloud PostgreSQL with more resources

### OpenAI API Issues
- Verify API key is correct
- Check API quota and billing
- Handle rate limits (implemented in code)

## Development

### Running Tests
```powershell
pytest tests/ -v
```

### Code Style
```powershell
# Format code
black src/

# Lint code
flake8 src/

# Type checking
mypy src/
```

## Performance Optimization

### Database Tuning
Edit `postgresql.conf`:
```ini
shared_buffers = 2GB
effective_cache_size = 6GB
work_mem = 256MB
maintenance_work_mem = 512MB
```

### Index Optimization
For large datasets (>100k cases), consider HNSW indexes instead of IVFFlat:
```sql
CREATE INDEX idx_embedding_facts_hnsw 
ON haystack_documents 
USING hnsw (embedding_facts vector_cosine_ops);
```

## License
[Add license information]

## Contributing
[Add contribution guidelines]

## Support
For issues and questions:
- GitHub Issues: https://github.com/G2703/CaseMind/issues
- Documentation: [Link to detailed docs]
