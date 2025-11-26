# CaseMind - Legal Case Similarity Search 🔍⚖️

AI-powered similarity search system for legal cases using **Haystack 2.0**, PostgreSQL, and pgvector.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![PostgreSQL](https://img.shields.io/badge/postgresql-14+-blue.svg)](https://www.postgresql.org/)
[![Haystack](https://img.shields.io/badge/haystack-2.0+-green.svg)](https://haystack.deepset.ai/)

---

## 🌟 Features

- **🔥 Haystack 2.0 Integration**: Production-ready AI orchestration framework
- **Dual Embedding Architecture**: Separate embeddings for case facts and metadata
- **Batch Processing**: Ingest entire folders of legal cases efficiently
- **Smart Duplicate Detection**: Avoid re-indexing cases using file hash and case ID
- **Cross-Encoder Re-ranking**: High-accuracy similarity scoring with Haystack rankers
- **Template-Based Extraction**: Structured fact extraction using legal ontology
- **Rich CLI Interface**: Beautiful terminal UI with progress tracking
- **Pipeline Architecture**: Declarative Haystack Pipelines with automatic optimization
- **PostgreSQL + pgvector**: Scalable vector similarity search with ACID guarantees
- **Modular Components**: Easy to extend with Haystack's component ecosystem

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- PostgreSQL 14+
- OpenAI API key

### Installation (Windows - Automated)

```powershell
# 1. Clone repository
git clone <repository-url>
cd CaseMind

# 2. Run automated setup (as Administrator)
.\setup_postgres.ps1

# 3. Configure environment
cp .env.example .env
# Edit .env with your credentials and OpenAI API key

# 4. Install Python dependencies
pip install -r requirements.txt

# 5. Validate setup
python validate_setup.py

# 6. Run application
python src/main.py
```

### Installation (Linux/macOS - Manual)

See **[QUICKSTART.md](QUICKSTART.md)** for detailed manual setup instructions.

---

## 📋 Usage Examples

### Batch Ingestion
```
Select option: 1
Enter folder path: cases/input_files/
✓ Processed: 45 / 50
```

### Find Similar Cases
```
Select option: 2
Enter query PDF: cases/test_case.pdf
Found 3 similar cases (scores: 0.89, 0.76, 0.63)
```

---

## 🏗️ Architecture

**Layered Architecture with SOLID Principles**

- **Presentation**: CLI with Rich UI
- **Pipelines**: Ingestion & Similarity Search orchestrators
- **Services**: PDF loader, extractors, embedders, duplicate checker
- **Infrastructure**: PostgreSQL + pgvector document store
- **Core**: Interfaces, models, configuration, exceptions

See **[DESIGN_DOCUMENT.md](DESIGN_DOCUMENT.md)** for complete architecture details.

---

## 📚 Documentation

- **[HAYSTACK_INTEGRATION.md](HAYSTACK_INTEGRATION.md)**: **⭐ NEW!** Complete Haystack 2.0 integration guide
- **[QUICKSTART.md](QUICKSTART.md)**: Complete setup guide for all platforms
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)**: Implementation details
- **[DESIGN_DOCUMENT.md](DESIGN_DOCUMENT.md)**: Architecture and design patterns
- **[README_HAYSTACK.md](README_HAYSTACK.md)**: Legacy Haystack documentation

### Migration to Haystack 2.0

CaseMind now uses **Haystack 2.0** for component-based AI orchestration. Benefits:

✅ **Production-Ready**: Battle-tested components from Haystack ecosystem  
✅ **Extensible**: Easy integration with 50+ Haystack components  
✅ **Observable**: Built-in pipeline visualization and logging  
✅ **Backward Compatible**: Existing code works with minimal changes  

**Quick Test**:
```bash
# Test Haystack components
python src/scripts/test_haystack_migration.py

# View migration details
python src/scripts/haystack_migration_report.py
```

See **[HAYSTACK_INTEGRATION.md](HAYSTACK_INTEGRATION.md)** for complete migration guide.

---

## 🛠️ Technology Stack

- **Haystack 2.0+**: NLP pipeline framework
- **PostgreSQL 14+ with pgvector**: Vector database
- **OpenAI GPT-4**: Metadata/fact extraction
- **Sentence Transformers**: Embeddings (all-mpnet-base-v2)
- **Cross-Encoder**: Re-ranking (ms-marco-MiniLM-L6-v2)
- **PyMuPDF**: PDF processing
- **Rich**: Terminal UI

---

## 🔧 Configuration

Key settings in `.env`:

```bash
POSTGRES_HOST=localhost
POSTGRES_DB=casemind
OPENAI_API_KEY=sk-your-key
TOP_K_SIMILAR_CASES=3
CROSS_ENCODER_THRESHOLD=0.0
```

---

## 🧪 Validation

```bash
# Validate complete setup
python validate_setup.py

# Initialize database
python src/scripts/init_database.py
```

---

## 📊 Performance

- **Ingestion**: 20-40 seconds per case
- **Similarity Search**: 2-5 seconds
- **Vector Retrieval**: <1 second (HNSW index)

---

## 🐛 Troubleshooting

See **[QUICKSTART.md](QUICKSTART.md)** for detailed troubleshooting guide.

Common issues:
- Database connection → Check PostgreSQL service
- pgvector not found → Install extension
- OpenAI API errors → Verify API key

---

## 📝 License

MIT License

---

## 🙏 Acknowledgments

Built using Haystack, pgvector, Sentence Transformers, and Rich.

**For the legal tech community** ❤️⚖️

---

# CaseMind - Original README — Legal AI Framework for IPC Case Processing

CaseMind is a lightweight legal case processing framework focused on extracting structured facts from court case documents (PDFs or text) using an AI-backed template system. The project was built to process Indian Penal Code (IPC) cases and organize facts into a 4-tier hierarchy suitable for downstream analysis and similarity/search applications.

## Key features

- Template-driven fact extraction (42 specialized templates for common legal categories and IPC sections)
- AI-powered fact extraction (GPT-4 / OpenAI API used by the `FactExtractor` module)
- Ontology-based template matching (uses `ontology_schema.json` to guide template selection)
- **Advanced similarity search with cross-encoder re-ranking** for finding most relevant similar cases
- Batch and single-file processing entry points
- Structured JSON output for each processed case (saved under `cases/extracted/`)

## Quick overview / architecture

Core entry points

- `src/main_pipeline.py` — Primary orchestrator for end-to-end processing
- `src/similarity_pipeline/similarity_search_pipeline.py` — **Advanced similarity search with cross-encoder re-ranking**
- `process_robbery_cases.py` — Batch processor for robbery/IPC 392 cases
- `embed_ipc_392_cases_combined.py` — Embedding & similarity analysis for IPC 392 cases

Core modules (high level)

- `PDFToMarkdownConverter` — (convert_pdf_to_md.py) converts PDFs into markdown/plain text
- `MetadataExtractor` — (extract_metadata.py) extracts case metadata and suggests a template
- `OntologyMatcher` — (ontology_matcher.py) picks the best template using ontology rules
- `TemplateLoader` — loads templates from `templates/`
- `FactExtractor` — (extract_facts.py) calls the OpenAI API to extract structured facts per template
- Storage & utils — helpers to save JSON, load inputs, and manage paths

Data shape

- Output files live in `cases/extracted/` with filenames like `Case Name_facts.json`.
- Each JSON follows a 4-tier fact hierarchy: determinative, material, contextual, procedural facts.

## Prerequisites

- Python 3.10+ recommended
- An OpenAI API key with access to GPT-4 (set via `OPENAI_API_KEY` environment variable)
- See `requirements.txt` for the minimal runtime dependencies (e.g., `openai`, `python-dotenv`).

## Installation

1. Create and activate a virtual environment (recommended):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

3. Add your OpenAI API key to environment (example using PowerShell):

```powershell
$env:OPENAI_API_KEY = "sk-..."
# Or add it to a .env file and ensure it's not committed (.gitignore already ignores .env)
```

## Usage

Note: The exact CLI parameters are intentionally minimal in this README — check script docstrings for up-to-date options.

Single-file processing (example):

```powershell
python src/main_pipeline.py --input cases/input_files/SomeCase.pdf
```

Batch processing (robbery cases example):

```powershell
python process_robbery_cases.py --input-dir cases/input_files/ --output-dir cases/extracted/
```

Embedding/similarity analysis for IPC 392 cases:

```powershell
python embed_ipc_392_cases_combined.py
```

If a script provides more flags, run it with `-h` to see options. The scripts in `src/` contain the implementation and more detailed usage examples.

## Directory layout (important files)

Top-level

- `cases/` — contains `input_files/` (raw inputs) and `extracted/` (JSON outputs)
- `src/` — source code for the processing pipeline
- `templates/` — JSON templates for different IPC sections and case categories
- `Ontology_schema\ontology_schema.json` — hierarchical ontology used by `OntologyMatcher`
- `requirements.txt` — Python dependencies
- `README.md` — this file

Templates

- `templates/` contains ~42 template JSON files such as `ipc_392.json`, `robbery.json`, `assault.json`, etc. Templates define expected fields and the fact hierarchy used by the `FactExtractor`.

## Tests

Run tests with pytest (project already uses `pytest`):

```powershell
python -m pytest -q
```

There are lightweight tests in `tests/` for repository-level checks (API keys, simple merges).

## Development notes

- The project was simplified from a heavier ML stack (removed pandas/numpy/faiss/spacy) and focuses on the template + OpenAI extraction flow.
- If you modify templates or `ontology_schema.json`, add corresponding unit tests to `tests/`.
- Common repos practices: format with `black`, lint with `flake8`.

## Untracked / ignored files

- The repo `.gitignore` is configured to ignore environment files (`.env`), virtual environments (e.g. `.venv`), and `cases/input_files/` to avoid committing sensitive/raw inputs.

## Troubleshooting

- If the pipeline fails when calling OpenAI: check `OPENAI_API_KEY`, network access, and API usage limits.
- If large PDFs cause truncation, split them or adjust the converter logic in `src/convert_pdf_to_md.py`.

## Similarity Search Pipeline

The enhanced similarity search pipeline (`src/similarity_pipeline/similarity_search_pipeline.py`) provides advanced case similarity matching with cross-encoder re-ranking:

### Features
- **12-step pipeline**: PDF → Markdown → Metadata → Template Matching → Fact Extraction → Embedding → Similarity → Cross-Encoder Re-ranking → Threshold Filtering → Results
- **Two-stage ranking**: Initial cosine similarity followed by cross-encoder re-ranking for higher precision
- **Threshold-based filtering**: Only display cases with cross-encoder scores above configurable threshold

### Usage

```python
from src.similarity_pipeline.similarity_search_pipeline import SimilarityCaseSearchPipeline

# Initialize pipeline
pipeline = SimilarityCaseSearchPipeline("config.json")

# Run complete pipeline
results = pipeline.run_complete_pipeline("path/to/case.pdf")
# Returns: List[Tuple[case_id, cosine_similarity, cross_encoder_score]]
```

### Configuration

Set these environment variables in your `.env` file:

```bash
# Initial similarity search
TOP_K_SIMILAR_CASES=10

# Cross-encoder re-ranking with threshold filtering
CROSS_ENCODER_MODEL=cross-encoder/ms-marco-MiniLM-L6-v2
CROSS_ENCODER_THRESHOLD=0.0  # Only cases above this score are displayed
```

### Pipeline Steps
1. Load PDF file
2. Convert to markdown
3-6. Extract metadata, match template, load template, extract facts
7. Generate vector embedding
8. Load existing case embeddings
9. Compute cosine similarity
10. Get top-K similar cases (excluding duplicates)
11. **Re-rank using cross-encoder and filter by threshold** (concatenated fact values)
12. Display cases above threshold

## Next steps / ideas

- Add small end-to-end example with a public, redacted PDF and expected JSON output for new contributors
- Add CI that runs the tests and a dry-run of the pipeline with a tiny sample case
- Provide a lightweight web UI to browse `cases/extracted/` and run similarity searches

## Contributing

- Open issues for bugs or feature requests.
- Submit PRs against `dev` (default branch is `main`). Include tests for new behavior.

## License & contact

See `LICENSE` if present. For questions, contact the repository owner or open an issue.

---

Last updated: 2025-11-12
