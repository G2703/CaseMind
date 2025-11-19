# Legal Case Similarity Search Pipeline

This pipeline processes a new PDF legal case document and finds the most similar cases from existing case embeddings.

## Features

- **Complete PDF-to-Similarity Pipeline**: Processes raw PDF files through all stages
- **Configurable Similarity Search**: Set the number of top similar cases via environment variable
- **Comprehensive Logging**: Detailed step-by-step progress tracking
- **Existing Infrastructure Integration**: Uses all existing CaseMind components

## Pipeline Steps

1. **Load PDF**: Validate and load the input PDF file
2. **Convert to Markdown**: Extract and clean text from PDF
3-6. **Complete Extraction**: Extract metadata, select template, and extract facts (integrated pipeline)
7. **Form Vector Embedding**: Generate embeddings for the extracted facts
8. **Load Stored Embeddings**: Load existing case embeddings from storage
9. **Compute Similarity**: Calculate cosine similarity between new and existing cases
10. **Get Top-K Similar**: Select the most similar cases
11. **Display Results**: Show the names and details of similar cases

## Quick Start

```bash
# Set environment variable
set TOP_K_SIMILAR_CASES=5

# Run pipeline
python similarity_search_pipeline.py path/to/your/case.pdf
```

## Usage Examples

### Command Line
```bash
python similarity_search_pipeline.py case.pdf --top-k 10
```

### Python Code
```python
from similarity_search_pipeline import SimilarityCaseSearchPipeline
pipeline = SimilarityCaseSearchPipeline('config.json')
results = pipeline.run_complete_pipeline('case.pdf')
```

## Environment Setup

Create a `.env` file or set environment variables:
```
OPENAI_API_KEY=your_key_here
TOP_K_SIMILAR_CASES=5
```