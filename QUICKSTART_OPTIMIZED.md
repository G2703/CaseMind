# CaseMind Optimized Pipeline - Quick Start

## 🚀 **GET STARTED IN 3 STEPS**

### **Step 1: Configure Environment**

```bash
# Copy template
cp .env.example .env

# Edit .env and set your OpenAI API key
OPENAI_API_KEY=your_key_here
OPENAI_RPM=3
```

### **Step 2: Test the Pipeline**

```bash
# Activate virtual environment
& .\venv\Scripts\Activate.ps1

# Health check (verify all components working)
python ingest_optimized_cli.py health

# Test with a single file
python ingest_optimized_cli.py ingest --file cases/input_files/case1.pdf
```

### **Step 3: Process Your Batch**

```bash
# Process all files with dashboard
python ingest_optimized_cli.py ingest --directory cases/input_files
```

---

## ⚡ **QUICK COMMANDS**

```bash
# Ingest single file
python ingest_optimized_cli.py ingest --file <path>

# Ingest directory
python ingest_optimized_cli.py ingest --directory <path>

# Allow re-ingestion
python ingest_optimized_cli.py ingest --directory <path> --allow-duplicates

# No dashboard (faster)
python ingest_optimized_cli.py ingest --directory <path> --no-dashboard

# Health check
python ingest_optimized_cli.py health

# View metrics
python ingest_optimized_cli.py metrics
```

---

## 📊 **WHAT YOU GET**

| Feature | Benefit |
|---------|---------|
| **2.4x Faster** | 100 files in 40 min vs 95 min |
| **Parallel PDF** | 3 workers process PDFs concurrently |
| **Smart Rate Limiting** | Never exceed OpenAI limits |
| **Batched Embedding** | 8x faster embedding generation |
| **Auto Retry** | Failed files automatically retried |
| **Live Dashboard** | Real-time progress monitoring |
| **Keep-Alive** | Resources reused between batches |
| **Error Tracking** | Detailed failure logs |

---

## 🎛️ **KEY SETTINGS**

Edit `.env` to tune performance:

```env
# Your OpenAI tier (critical!)
OPENAI_RPM=3           # Free: 3, Tier 1: 60, Tier 2: 500+

# Parallel workers (match CPU cores)
MAX_WORKERS=3          # Default: 3

# Batch sizes (higher = faster, more memory)
BATCH_SIZE_EMBEDDING=100   # Default: 100
BATCH_SIZE_WEAVIATE=200    # Default: 200
```

---

## 🎯 **PERFORMANCE TIPS**

1. **Upgrade OpenAI Tier** → Biggest speedup (3 RPM → 60 RPM = 20x faster extraction!)
2. **More CPU Cores** → Increase `MAX_WORKERS`
3. **More RAM** → Increase batch sizes
4. **Keep Dashboard** → Monitor bottlenecks
5. **Check Health** → Before large batches

---

## 🔍 **TROUBLESHOOTING**

| Problem | Solution |
|---------|----------|
| Rate limit errors | Reduce `OPENAI_RPM` |
| Slow startup | Set `EMBEDDING_WARMUP=false` |
| Out of memory | Reduce batch sizes |
| Connection errors | Increase `WEAVIATE_POOL_SIZE` |
| Pipeline hangs | Run `health` command |

---

## 📁 **OUTPUT FILES**

- `logs/casemind.log` - Full execution log
- `logs/failed_files.json` - Failed files with errors
- `logs/metrics.json` - Performance metrics

---

## 💡 **PRO TIPS**

✅ Always run `health` check first  
✅ Start with small batch (10 files) to test  
✅ Review `failed_files.json` for errors  
✅ Use `--no-dashboard` for huge batches (1000+ files)  
✅ Keep dashboard enabled for monitoring  

---

## 📚 **FULL DOCUMENTATION**

See `OPTIMIZED_PIPELINE_GUIDE.md` for:
- Detailed architecture
- Advanced configuration
- Performance benchmarks
- Troubleshooting guide

---

**Happy processing!** 🎉
