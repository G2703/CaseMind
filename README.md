# CaseMind — Legal AI Framework for IPC Case Processing

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
