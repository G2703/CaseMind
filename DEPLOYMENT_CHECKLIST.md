# CaseMind - Deployment Checklist

Use this checklist to ensure CaseMind is properly set up and ready for use.

---

## ✅ Pre-Installation Checklist

### System Requirements
- [ ] Python 3.9 or higher installed
- [ ] PostgreSQL 14 or higher installed
- [ ] 8GB+ RAM recommended
- [ ] 10GB+ free disk space
- [ ] Internet connection (for model downloads)

### API Access
- [ ] OpenAI API account created
- [ ] OpenAI API key obtained
- [ ] Billing enabled on OpenAI account
- [ ] API rate limits understood

---

## ✅ Installation Checklist

### PostgreSQL Setup
- [ ] PostgreSQL service running
- [ ] Can connect with `psql -U postgres`
- [ ] Database `casemind` created
- [ ] pgvector extension installed
- [ ] pgvector extension enabled in database

### Python Environment
- [ ] Virtual environment created (recommended)
- [ ] Virtual environment activated
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] No import errors when running `python -c "import psycopg2; import openai; import sentence_transformers"`

### Configuration
- [ ] `.env` file created (copied from `.env.example`)
- [ ] PostgreSQL credentials configured in `.env`
- [ ] OpenAI API key set in `.env`
- [ ] Template paths verified in `.env`
- [ ] Ontology schema path verified in `.env`

### Database Schema
- [ ] Ran `python src/scripts/init_database.py`
- [ ] No errors during schema creation
- [ ] `documents` table exists
- [ ] All 8 indexes created
- [ ] pgvector extension shows in `\dx` (psql command)

---

## ✅ Validation Checklist

### Automated Validation
- [ ] Ran `python validate_setup.py`
- [ ] All checks passed:
  - [ ] Python version check
  - [ ] Environment file exists
  - [ ] Config files exist
  - [ ] Directory structure verified
  - [ ] Python packages installed
  - [ ] Database connection successful
  - [ ] AI models loaded

### Manual Verification
- [ ] Can start application (`python src/main.py`)
- [ ] Main menu displays correctly
- [ ] Health check (option 4) shows all systems healthy
- [ ] Database statistics (option 3) displays without errors

---

## ✅ First Use Checklist

### Test Ingestion
- [ ] Prepared test folder with 2-3 PDF cases
- [ ] Selected option 1 (Ingest Cases)
- [ ] Batch ingestion completed without errors
- [ ] Statistics show correct number of cases
- [ ] No duplicate cases when re-running same folder

### Test Similarity Search
- [ ] Prepared test query PDF
- [ ] Selected option 2 (Find Similar Cases)
- [ ] Query case ingested successfully
- [ ] Similar cases retrieved and displayed
- [ ] Results show reasonable similarity scores (>0.5)
- [ ] Results formatted correctly in table

### Test Both Search Modes
- [ ] Tested facts similarity search (mode 1)
- [ ] Tested metadata similarity search (mode 2)
- [ ] Both modes return results
- [ ] Results differ between modes (as expected)

---

## ✅ Production Readiness Checklist

### Security
- [ ] `.env` file NOT committed to version control
- [ ] `.env` file in `.gitignore`
- [ ] PostgreSQL password is strong
- [ ] OpenAI API key kept secret
- [ ] Database accessible only from localhost (or secured)

### Performance
- [ ] Database indexes verified (`\di` in psql)
- [ ] HNSW indexes on both embedding columns
- [ ] Statistics updated (`ANALYZE documents;` in psql)
- [ ] Query performance acceptable (<5s per search)

### Monitoring
- [ ] Logs directory exists (`logs/`)
- [ ] Log file created (`logs/casemind.log`)
- [ ] Log level set appropriately (INFO for production)
- [ ] Errors logged correctly

### Backup
- [ ] Database backup strategy defined
- [ ] Regular backups scheduled
- [ ] Backup restoration tested
- [ ] `.env` file backed up securely

### Documentation
- [ ] Team members familiar with QUICKSTART.md
- [ ] Configuration documented
- [ ] Custom templates documented (if added)
- [ ] Troubleshooting procedures documented

---

## ✅ Operational Checklist

### Daily Operations
- [ ] Monitor disk space (PostgreSQL + logs)
- [ ] Check application logs for errors
- [ ] Monitor OpenAI API usage and costs
- [ ] Verify database backups completed

### Weekly Maintenance
- [ ] Review error logs
- [ ] Check database size growth
- [ ] Vacuum database if needed (`VACUUM ANALYZE documents;`)
- [ ] Update statistics
- [ ] Review similarity search accuracy

### Monthly Tasks
- [ ] Review and optimize database indexes
- [ ] Check for model updates (Sentence Transformers)
- [ ] Review OpenAI costs and optimize if needed
- [ ] Archive old logs
- [ ] Update documentation

---

## ✅ Troubleshooting Checklist

### Database Issues
- [ ] PostgreSQL service running?
- [ ] Can connect manually with psql?
- [ ] Credentials correct in `.env`?
- [ ] pgvector extension enabled?
- [ ] Schema created without errors?

### Ingestion Issues
- [ ] PDF files readable?
- [ ] OpenAI API key valid?
- [ ] API rate limits not exceeded?
- [ ] Sufficient disk space?
- [ ] Network connectivity OK?

### Search Issues
- [ ] Query case ingested successfully?
- [ ] Database has indexed cases?
- [ ] Embeddings generated correctly?
- [ ] Indexes on embedding columns?
- [ ] Cross-encoder model loaded?

### Performance Issues
- [ ] Database indexes exist and used?
- [ ] Statistics up to date?
- [ ] Sufficient RAM available?
- [ ] Network latency acceptable?
- [ ] OpenAI API response time normal?

---

## ✅ Scale-Up Checklist

### When Growing Beyond 1,000 Cases
- [ ] Monitor database size
- [ ] Consider connection pooling
- [ ] Optimize batch size
- [ ] Review index strategy
- [ ] Consider read replicas

### When Growing Beyond 10,000 Cases
- [ ] Implement caching layer
- [ ] Partition tables (if needed)
- [ ] Optimize HNSW parameters
- [ ] Consider dedicated database server
- [ ] Implement async job queue

### When Adding Team Members
- [ ] Document custom templates
- [ ] Standardize configuration
- [ ] Set up shared development environment
- [ ] Document deployment procedures
- [ ] Implement version control best practices

---

## ✅ Advanced Features Checklist

### Custom Templates
- [ ] Template JSON created in `templates/`
- [ ] Template added to ontology schema
- [ ] Template tested with sample cases
- [ ] Documentation updated

### Custom Models
- [ ] New model tested for compatibility
- [ ] Embedding dimensions match (768 for default)
- [ ] Performance benchmarked
- [ ] Configuration updated

### API/Web Interface (Future)
- [ ] Authentication implemented
- [ ] Rate limiting configured
- [ ] CORS configured correctly
- [ ] API documentation created
- [ ] Security audit completed

---

## ✅ Sign-Off Checklist

### Development Team
- [ ] Code reviewed
- [ ] Tests passed (if implemented)
- [ ] Documentation complete
- [ ] Deployment guide reviewed

### Operations Team
- [ ] Infrastructure ready
- [ ] Monitoring configured
- [ ] Backup strategy in place
- [ ] Disaster recovery tested

### End Users
- [ ] Training completed
- [ ] User guide provided
- [ ] Support channels established
- [ ] Feedback mechanism in place

---

## 📝 Notes Section

**Installation Date**: _______________

**Installed By**: _______________

**Database Version**: _______________

**Python Version**: _______________

**Initial Case Count**: _______________

**Known Issues**:
- 
- 
- 

**Custom Modifications**:
- 
- 
- 

---

## ✅ Final Sign-Off

- [ ] All critical items checked
- [ ] System tested end-to-end
- [ ] Documentation reviewed
- [ ] Ready for production use

**Signed**: _______________ **Date**: _______________

---

**Keep this checklist for future reference and maintenance cycles.**
