# CaseMind - Quick Start Guide

Complete setup guide for CaseMind legal case similarity search system.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Quick Setup (Automated)](#quick-setup-automated)
3. [Manual Setup](#manual-setup)
4. [Configuration](#configuration)
5. [First Run](#first-run)
6. [Usage](#usage)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software
- **Python 3.9+**: [Download Python](https://www.python.org/downloads/)
- **PostgreSQL 14+**: Database server
- **Git**: For cloning the repository

### Required API Keys
- **OpenAI API Key**: For metadata and fact extraction ([Get key](https://platform.openai.com/api-keys))

---

## Quick Setup (Automated)

### Windows

Run the automated setup script:

```powershell
# Run PowerShell as Administrator
.\setup_postgres.ps1
```

This script will:
1. Install PostgreSQL (if needed)
2. Create `casemind` database
3. Install pgvector extension
4. Initialize database schema
5. Verify setup

### Manual Alternative (All Platforms)

If the automated script doesn't work, follow the [Manual Setup](#manual-setup) section.

---

## Manual Setup

### Step 1: Install PostgreSQL

#### Windows
```powershell
# Using Chocolatey
choco install postgresql

# Or download installer from:
# https://www.postgresql.org/download/windows/
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

#### macOS
```bash
brew install postgresql
```

### Step 2: Start PostgreSQL Service

#### Windows
```powershell
# Start service
Start-Service postgresql-x64-16  # Adjust version number

# Or use Services GUI (services.msc)
```

#### Linux
```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql  # Auto-start on boot
```

#### macOS
```bash
brew services start postgresql
```

### Step 3: Create Database

```bash
# Connect as postgres user
psql -U postgres

# Create database
CREATE DATABASE casemind;

# Exit psql
\q
```

### Step 4: Install pgvector Extension

#### Windows
Follow pgvector Windows installation guide:
https://github.com/pgvector/pgvector#windows

#### Linux/macOS
```bash
# Install build dependencies
sudo apt install build-essential postgresql-server-dev-14

# Clone and build pgvector
cd /tmp
git clone --branch v0.5.1 https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

Enable the extension:
```bash
psql -U postgres -d casemind -c "CREATE EXTENSION vector;"
```

### Step 5: Install Python Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 6: Initialize Database Schema

```bash
# Run initialization script
python src/scripts/init_database.py
```

Expected output:
```
✓ Database connection successful
✓ pgvector extension enabled
✓ Database schema created
✓ Database verified
```

---

## Configuration

### Step 1: Create .env File

```bash
# Copy example configuration
cp .env.example .env

# Edit .env file with your settings
```

### Step 2: Update Configuration

Edit `.env` file:

```bash
# PostgreSQL Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=casemind
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_actual_password

# OpenAI API Key (REQUIRED)
OPENAI_API_KEY=sk-your-actual-openai-key
OPENAI_MODEL=gpt-4

# Search Configuration
TOP_K_SIMILAR_CASES=3
CROSS_ENCODER_THRESHOLD=0.0

# Logging
LOG_LEVEL=INFO
```

### Step 3: Verify Configuration

Test database connection:
```bash
python src/scripts/init_database.py
```

---

## First Run

### Start the Application

```bash
python src/main.py
```

You should see:
```
╔══════════════════════════════════════════╗
║   CaseMind Legal Similarity Search       ║
║   AI-powered similarity search           ║
╚══════════════════════════════════════════╝

Initializing backend services...
  ✓ Backend initialized successfully
  ℹ Database: 0 cases indexed

Select an option:
  1  Ingest Cases (Batch)
  2  Find Similar Cases
  3  Database Statistics
  4  Health Check
  5  Exit
```

---

## Usage

### 1. Batch Ingestion

Ingest a folder of PDF cases:

```
Select option: 1
Enter folder path: C:\Users\YourName\Documents\cases\input_files
Found 50 PDF files
Proceed with batch ingestion? [Y/n]: Y

Processing... ━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%

✓ Processed: 45 / 50
⊘ Skipped (Duplicates): 3
✗ Failed: 2
Success Rate: 90.0%
```

### 2. Find Similar Cases

Search for similar cases:

```
Select option: 2
Enter path to query PDF: C:\Users\YourName\Documents\test_case.pdf

Search Mode:
  1. Search by Case Facts (default)
  2. Search by Case Metadata (case name, court, sections)
Select search mode [1/2]: 1

Processing query case...
Running similarity pipeline...

╔════════════════════════════════════════╗
║  📋 Case Metadata                      ║
╚════════════════════════════════════════╝
Case Title: Ram Kumar vs. State of UP
Case ID: CID_20240101_RAM_KUMAR_VS_STATE_OF_UP
Court: High Court of Allahabad
Sections: IPC 302, IPC 120B

┏━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┓
┃ Rank ┃ Case Title      ┃ Court     ┃ Date     ┃ Score  ┃
┣━━━━━━╋━━━━━━━━━━━━━━━━━╋━━━━━━━━━━━╋━━━━━━━━━━╋━━━━━━━━┫
┃ 1    ┃ Similar Case 1  ┃ High Ct   ┃ 2023-05  ┃ 0.892  ┃
┃ 2    ┃ Similar Case 2  ┃ Supreme   ┃ 2022-11  ┃ 0.756  ┃
┃ 3    ┃ Similar Case 3  ┃ High Ct   ┃ 2021-08  ┃ 0.634  ┃
┗━━━━━━┻━━━━━━━━━━━━━━━━━┻━━━━━━━━━━━┻━━━━━━━━━━┻━━━━━━━━┛

✓ Found 3 similar cases
```

### 3. Database Statistics

View database statistics:

```
Select option: 3

╔════════════════════════════════════════╗
║  📊 Database Statistics                ║
╚════════════════════════════════════════╝
Total Cases: 150
Unique Case IDs: 148
Oldest Case: 2018-01-15
Newest Case: 2024-03-20
Database Size: 45.2 MB
```

### 4. Health Check

Check system health:

```
Select option: 4

╔════════════════════════════════════════╗
║  🏥 System Health Check                ║
╚════════════════════════════════════════╝
PostgreSQL Database    ✓ Healthy
pgvector Extension     ✓ Healthy
Embedding Service      ✓ Healthy
Cross-Encoder          ✓ Healthy
OpenAI API             ✓ Healthy

All systems operational!
```

---

## Troubleshooting

### Database Connection Failed

**Error**: `Connection to database failed`

**Solutions**:
1. Check PostgreSQL is running:
   ```powershell
   Get-Service postgresql*  # Windows
   sudo systemctl status postgresql  # Linux
   ```

2. Verify credentials in `.env`:
   ```
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=your_password
   ```

3. Test connection manually:
   ```bash
   psql -U postgres -d casemind
   ```

### pgvector Extension Not Found

**Error**: `pgvector extension not found`

**Solutions**:
1. Install pgvector (see Step 4 in Manual Setup)
2. Enable extension:
   ```bash
   psql -U postgres -d casemind -c "CREATE EXTENSION vector;"
   ```

### OpenAI API Errors

**Error**: `OpenAI API authentication failed`

**Solutions**:
1. Check API key in `.env`:
   ```
   OPENAI_API_KEY=sk-your-actual-key
   ```

2. Verify key is valid at: https://platform.openai.com/api-keys

3. Check rate limits and billing

### Model Download Issues

**Error**: `Failed to download embedding model`

**Solutions**:
1. Check internet connection
2. Models will download automatically on first use
3. Location: `~/.cache/huggingface/hub/`

### Out of Memory

**Error**: `Out of memory during batch processing`

**Solutions**:
1. Process smaller batches
2. Increase system RAM
3. Reduce `TOP_K_SIMILAR_CASES` in `.env`

### Schema Already Exists

**Error**: `Table already exists`

**Solution**: This is normal if reinitializing. To reset:
```bash
psql -U postgres -d casemind -c "DROP TABLE IF EXISTS documents CASCADE;"
python src/scripts/init_database.py
```

---

## Advanced Configuration

### Custom Embedding Models

Edit `.env`:
```
# Use different sentence transformer
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-mpnet-base-v2

# Or OpenAI embeddings (requires modification)
# EMBEDDING_MODEL=text-embedding-ada-002
```

### Adjust Search Sensitivity

```
# Return more results (1-10)
TOP_K_SIMILAR_CASES=5

# Higher threshold = only very similar cases (0.0-1.0)
CROSS_ENCODER_THRESHOLD=0.5
```

### Enable Debug Logging

```
LOG_LEVEL=DEBUG
LOG_FILE=logs/casemind.log
```

---

## Next Steps

1. **Ingest your case database**: Use batch ingestion for your PDF collection
2. **Test similarity search**: Try different query cases
3. **Optimize thresholds**: Adjust `CROSS_ENCODER_THRESHOLD` based on results
4. **Explore metadata search**: Use option 2 with metadata mode for entity-based retrieval

---

## Support

For issues or questions:
- Check `logs/casemind.log` for detailed error messages
- Review `DESIGN_DOCUMENT.md` for architecture details
- See `README_HAYSTACK.md` for Haystack-specific information

---

**Congratulations!** You're now ready to use CaseMind for legal case similarity search. 🎉
