# CaseMind Similarity Analyzer CLI - Setup Guide

## 📦 Installation Steps

### Step 1: Install Rich Library

Open terminal in the CaseMind directory and run:

```bash
pip install rich
```

Or install all requirements:

```bash
pip install -r requirements.txt
```

### Step 2: Verify Installation

Run the test script:

```bash
python src/cli/test_cli.py
```

Expected output:
```
Testing imports...
✓ Rich library imports successful
✓ Similarity pipeline import successful
✓ Rich CLI import successful

======================================================================
All imports successful! CLI is ready to use.
======================================================================

Testing CLI initialization...
✓ CLI initialized successfully
  Color scheme: ['primary', 'secondary', 'success', 'warning', 'danger', 'info', 'text', 'muted']

======================================================================
READY FOR TESTING!
======================================================================

You can now run the CLI with:
  python src/cli/rich_similarity_cli.py

Or with a specific file:
  python src/cli/rich_similarity_cli.py --pdf "cases/input_files/..."
```

### Step 3: Test Run

Try a test run with a sample PDF:

```bash
python src/cli/rich_similarity_cli.py --pdf "cases\input_files\Cases\Dowry Death\Aakash Tiwari & Anr Vs St of Mah.pdf"
```

---

## 🔧 Prerequisites

### Required Components

1. **Python 3.8+** ✓ (Already installed)
2. **CaseMind Project** ✓ (Current workspace)
3. **Similarity Pipeline** ✓ (src/similarity_pipeline)
4. **Case Database** ✓ (cases/extracted/)
5. **Embeddings** ✓ (Embedding results/)
6. **Rich Library** ⚠️ (Need to install)

### Environment Variables

Check your `.env` file or set these:

```env
# OpenAI API Key (for metadata extraction)
OPENAI_API_KEY=your_api_key_here

# Similarity search configuration
TOP_K_SIMILAR_CASES=5
CROSS_ENCODER_MODEL=cross-encoder/ms-marco-MiniLM-L6-v2
CROSS_ENCODER_THRESHOLD=0.0
```

---

## 📁 File Structure

After setup, your structure should look like:

```
CaseMind/
├── src/
│   ├── cli/                          # ← NEW: CLI Interface
│   │   ├── rich_similarity_cli.py    # Main CLI application
│   │   ├── test_cli.py               # Test script
│   │   ├── README.md                 # CLI documentation
│   │   ├── DEMO_REFERENCE.md         # Demo guide
│   │   ├── IMPLEMENTATION_SUMMARY.md # Implementation details
│   │   └── VISUAL_EXAMPLES.md        # Output examples
│   ├── similarity_pipeline/
│   │   └── similarity_search_pipeline.py
│   └── bg_creation/
│       └── (various modules)
├── cases/
│   ├── extracted/                    # Case database
│   └── input_files/                  # Test PDFs
├── Embedding results/                # Pre-computed embeddings
├── config.json                       # Configuration
├── requirements.txt                  # Dependencies (updated)
├── launch_similarity_cli.bat         # ← NEW: Quick launcher
└── .env                             # Environment variables
```

---

## 🧪 Testing Checklist

### Basic Tests

- [ ] Import test passes
  ```bash
  python src/cli/test_cli.py
  ```

- [ ] CLI launches without errors
  ```bash
  python src/cli/rich_similarity_cli.py
  ```

- [ ] File input validation works
  - Try invalid path (should show error)
  - Try non-PDF file (should show error)
  - Try valid PDF (should accept)

- [ ] Processing completes successfully
  - All stages show animations
  - No exceptions thrown

- [ ] Results display correctly
  - Cosine similarity table appears
  - Final results show metadata
  - Scores are color-coded

### Advanced Tests

- [ ] Multiple PDFs work
- [ ] Different case types work (IPC 302, 307, 498A, etc.)
- [ ] Threshold filtering works
- [ ] Metadata extraction works
- [ ] Case summaries display

---

## ⚙️ Configuration

### Default Settings

The CLI uses these defaults from `config.json`:

```json
{
  "openai_api_key": "from_env",
  "embedding_model": "all-mpnet-base-v2",
  "embedding_output_dir": "Embedding results",
  "ontology_path": "Ontology_schema/ontology_schema.json",
  "templates_dir": "templates"
}
```

### Customization Options

#### 1. Change Top-K (number of results)

In `.env`:
```env
TOP_K_SIMILAR_CASES=10
```

Or via command line:
```bash
python src/similarity_pipeline/similarity_search_pipeline.py --pdf "..." --top-k 10
```

#### 2. Change Threshold

In `.env`:
```env
CROSS_ENCODER_THRESHOLD=0.3
```

Higher = more selective, Lower = more results

#### 3. Change Cross-Encoder Model

In `.env`:
```env
CROSS_ENCODER_MODEL=cross-encoder/ms-marco-MiniLM-L12-v2
```

#### 4. Customize Colors

Edit `src/cli/rich_similarity_cli.py`:

```python
self.colors = {
    'primary': '#00d4ff',      # Your brand color
    'secondary': '#7c3aed',    # Your accent color
    # ... etc
}
```

---

## 🐛 Common Issues & Solutions

### Issue 1: "ModuleNotFoundError: No module named 'rich'"

**Solution:**
```bash
pip install rich
```

### Issue 2: "ModuleNotFoundError: No module named 'similarity_search_pipeline'"

**Cause:** Python path issue

**Solution:** Run from project root:
```bash
cd C:\Users\gayat\OneDrive\Documents\CaseMind
python src/cli/rich_similarity_cli.py
```

### Issue 3: "No cases found above threshold"

**Cause:** Threshold too high

**Solutions:**
1. Lower threshold in .env: `CROSS_ENCODER_THRESHOLD=0.0`
2. Check if embeddings exist in `Embedding results/`
3. Verify cases in `cases/extracted/`

### Issue 4: "OpenAI API error"

**Cause:** API key issue

**Solution:** 
1. Check `.env` has valid `OPENAI_API_KEY`
2. Verify API key has credits
3. Check internet connection

### Issue 5: Slow processing

**Cause:** Normal for first run (model loading)

**Solutions:**
1. Subsequent runs will be faster
2. Models are cached after first load
3. Consider GPU acceleration for production

### Issue 6: "File not found" error

**Cause:** Incorrect path

**Solutions:**
1. Use absolute paths
2. Use forward slashes or double backslashes
3. Wrap path in quotes if it has spaces

---

## 🚀 Quick Start for Demo

### Option 1: Batch File (Windows)

Double-click `launch_similarity_cli.bat`

### Option 2: PowerShell

```powershell
cd "C:\Users\gayat\OneDrive\Documents\CaseMind"
python src/cli/rich_similarity_cli.py
```

### Option 3: Command Prompt

```cmd
cd C:\Users\gayat\OneDrive\Documents\CaseMind
python src\cli\rich_similarity_cli.py
```

---

## 📊 Performance Expectations

### First Run
- Model loading: 5-10 seconds
- PDF processing: 5-10 seconds
- Embedding generation: 2-5 seconds
- Similarity computation: 1-2 seconds
- Cross-encoder re-ranking: 3-5 seconds
- **Total: 15-30 seconds**

### Subsequent Runs
- Models cached: 0 seconds
- PDF processing: 5-10 seconds
- Rest same as above
- **Total: 10-20 seconds**

### Database Size Impact
- Small database (<100 cases): Fast
- Medium database (100-1000 cases): Normal
- Large database (>1000 cases): May need optimization

---

## 🔐 Security Notes

### Local Processing
- PDF text extraction: Local
- Embeddings generation: Local
- Similarity computation: Local
- Cross-encoder: Local

### External API Calls
- Metadata extraction: OpenAI API (can be replaced)
- Template matching: Local
- Fact extraction: OpenAI API (can be replaced)

### Data Privacy
- No data sent to external services except OpenAI for extraction
- Case database stays local
- Embeddings stay local
- Results stay local

---

## 📈 Next Steps

After successful setup:

1. **Test with sample cases** ✓
2. **Customize colors/branding** (optional)
3. **Prepare demo script** (see DEMO_REFERENCE.md)
4. **Practice the demo** 
5. **Show to client** 🎉

---

## 💬 Support

### Documentation
- `README.md` - CLI overview
- `DEMO_REFERENCE.md` - Demo guide with script
- `VISUAL_EXAMPLES.md` - Output examples
- `IMPLEMENTATION_SUMMARY.md` - Technical details

### Debugging
1. Run `test_cli.py` to verify setup
2. Check logs in terminal for errors
3. Verify all prerequisites are met
4. Review configuration files

### Development
- CLI code: `src/cli/rich_similarity_cli.py`
- Pipeline code: `src/similarity_pipeline/similarity_search_pipeline.py`
- Config: `config.json`
- Environment: `.env`

---

## ✅ Setup Complete!

If you've completed all steps and tests pass, you're ready for the demo!

**Final checklist:**
- [x] Rich installed
- [x] Test script passes
- [x] CLI launches successfully
- [x] Sample PDF processes correctly
- [x] Results display properly
- [x] Documentation reviewed

**You're all set! 🎉**

Run the demo with confidence:
```bash
python src/cli/rich_similarity_cli.py
```

Good luck! 🚀
