# Hybrid Search Strategy for CaseMind

## Overview
CaseMind uses a hybrid embedding approach that combines **facts embeddings** and **metadata embeddings** for optimal case retrieval.

---

## Embedding Architecture

### Phase 1: Case Summarization
Creates **7 section-specific embeddings**:
1. `metadata_embedding` - Case metadata (court, parties, sections, dates)
2. `case_facts_embedding` - Prosecution & defence versions, timeline
3. `issues_embedding` - Legal questions for determination
4. `evidence_embedding` - Witnesses, medical, forensic, documentary
5. `arguments_embedding` - Prosecution & defence arguments
6. `reasoning_embedding` - Court's analysis and findings
7. `judgement_embedding` - Final decision and sentence

### Phase 2: Template-Based Extraction
Creates **1 primary search embedding**:
- `facts_embedding` - Filled template with **Tiers 1-3 only**
  - Tier 1: Determinative Facts
  - Tier 2: Material Facts
  - Tier 3: Contextual Facts
  - **Tier 4 EXCLUDED** (metadata already captured in Phase 1)

---

## Why Tier 4 is Excluded

**Tier 4 (Procedural Facts)** contains metadata like:
- Case number, case title
- Court name, judges
- Parties, counsel
- Judgment date
- Sections invoked

**Problem**: When we pass only `case_facts` + `evidence` to the LLM in Phase 2, it can't fill Tier 4 fields (they'd be empty).

**Solution**: 
- Remove Tier 4 from fact extraction prompt
- Keep `facts_embedding` = pure case narrative (Tiers 1-3)
- Use existing `metadata_embedding` from Phase 1 for procedural info

---

## Hybrid Search Strategy

### Basic Formula
```python
similarity_score = α * fact_similarity + β * metadata_similarity
```

Where:
- `fact_similarity` = cosine similarity between query and `facts_embedding`
- `metadata_similarity` = cosine similarity between query and `metadata_embedding`
- `α + β = 1` (weights sum to 1)

---

## Recommended Weight Configurations

### 1. **Default Search** (General Queries)
```python
α = 0.7  # Facts weight
β = 0.3  # Metadata weight
```
**Use when**: User asks general questions like "find similar cases" or "cases about assault"

**Example**:
```
Query: "Cases where accused was acquitted due to lack of evidence"
→ Prioritize case facts (acquittal, evidence) over metadata
```

---

### 2. **Fact-Heavy Search** (Narrative Queries)
```python
α = 0.85
β = 0.15
```
**Use when**: Query focuses on case narrative, events, evidence, arguments

**Examples**:
- "Cases where medical evidence contradicted witness testimony"
- "Cases involving recovery of weapons from accused"
- "Self-defense arguments accepted by court"

---

### 3. **Metadata-Heavy Search** (Procedural Queries)
```python
α = 0.3
β = 0.7
```
**Use when**: Query focuses on court, judge, parties, sections, dates

**Examples**:
- "Cases decided by Justice XYZ"
- "IPC 376 cases from Delhi High Court"
- "Cases against State of UP in 2023"
- "Cases where accused represented by Advocate ABC"

---

### 4. **Balanced Search** (Mixed Queries)
```python
α = 0.5
β = 0.5
```
**Use when**: Query contains both factual and metadata elements

**Examples**:
- "IPC 302 cases where prosecution failed to prove motive"
- "Supreme Court judgments on credibility of eyewitness testimony"

---

## Implementation Examples

### Example 1: Simple Hybrid Search
```python
def hybrid_search(query: str, top_k: int = 10, alpha: float = 0.7):
    """
    Hybrid search combining facts and metadata embeddings.
    
    Args:
        query: User search query
        top_k: Number of results to return
        alpha: Weight for facts_embedding (1-alpha = metadata weight)
    """
    from sentence_transformers import SentenceTransformer
    import psycopg2
    
    # Embed query
    model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
    query_emb = model.encode(query).tolist()
    
    # Connect to database
    conn = psycopg2.connect(...)
    cursor = conn.cursor()
    
    # Hybrid search query
    beta = 1 - alpha
    cursor.execute(f"""
        SELECT 
            file_id,
            case_id,
            case_title,
            summary,
            factual_summary,
            ({alpha} * (1 - (facts_embedding <=> %s::vector))) + 
            ({beta} * (1 - (metadata_embedding <=> %s::vector))) AS hybrid_score
        FROM legal_cases
        WHERE facts_embedding IS NOT NULL 
          AND metadata_embedding IS NOT NULL
        ORDER BY hybrid_score DESC
        LIMIT %s;
    """, (query_emb, query_emb, top_k))
    
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return results
```

### Example 2: Query-Adaptive Weighting
```python
def adaptive_hybrid_search(query: str, top_k: int = 10):
    """
    Automatically adjust weights based on query content.
    """
    query_lower = query.lower()
    
    # Metadata indicators
    metadata_keywords = [
        'court', 'judge', 'justice', 'ipc', 'section', 
        'supreme court', 'high court', 'district court',
        'year', 'date', 'counsel', 'advocate', 'state of'
    ]
    
    # Fact indicators
    fact_keywords = [
        'evidence', 'witness', 'accused', 'victim', 'incident',
        'motive', 'weapon', 'injury', 'testimony', 'recovery',
        'argument', 'prosecution', 'defence', 'acquittal', 'conviction'
    ]
    
    metadata_count = sum(1 for kw in metadata_keywords if kw in query_lower)
    fact_count = sum(1 for kw in fact_keywords if kw in query_lower)
    
    total = metadata_count + fact_count
    if total == 0:
        # Default: fact-heavy
        alpha = 0.7
    else:
        # Adaptive weighting
        alpha = max(0.3, min(0.85, fact_count / total))
    
    return hybrid_search(query, top_k, alpha)
```

### Example 3: Multi-Stage Retrieval
```python
def multi_stage_search(query: str, top_k: int = 10):
    """
    Stage 1: Retrieve top 50 by facts_embedding
    Stage 2: Re-rank using hybrid score
    """
    # Stage 1: Fast facts-only retrieval
    facts_results = facts_only_search(query, top_k=50)
    
    # Stage 2: Re-rank with metadata
    query_emb = embed(query)
    re_ranked = []
    
    for case in facts_results:
        fact_sim = cosine(query_emb, case.facts_embedding)
        meta_sim = cosine(query_emb, case.metadata_embedding)
        
        hybrid_score = 0.7 * fact_sim + 0.3 * meta_sim
        re_ranked.append((case, hybrid_score))
    
    re_ranked.sort(key=lambda x: x[1], reverse=True)
    return re_ranked[:top_k]
```

---

## Advanced: Section-Specific Search

You can also search specific sections using the other 5 embeddings:

```python
def section_specific_search(query: str, section: str, top_k: int = 10):
    """
    Search specific sections of case summaries.
    
    Args:
        section: 'case_facts', 'evidence', 'arguments', 'reasoning', 'judgement'
    """
    embedding_column = f"{section}_embedding"
    
    query_emb = embed(query)
    
    cursor.execute(f"""
        SELECT file_id, case_id, case_title,
               1 - ({embedding_column} <=> %s::vector) AS similarity
        FROM legal_cases
        WHERE {embedding_column} IS NOT NULL
        ORDER BY similarity DESC
        LIMIT %s;
    """, (query_emb, top_k))
    
    return cursor.fetchall()
```

**Use cases**:
- "Find cases with similar evidence" → `section='evidence'`
- "Find cases with similar legal reasoning" → `section='reasoning'`
- "Find cases with similar arguments" → `section='arguments'`

---

## Performance Considerations

### Storage
- 8 embeddings per case × 768 dimensions = ~6KB per case
- 10,000 cases = ~60MB for all embeddings

### Search Speed
- **Facts-only**: ~5-10ms (single similarity calc)
- **Hybrid**: ~8-15ms (two similarity calcs + weighted sum)
- **Multi-section**: ~20-30ms (multiple similarity calcs)

### Optimization Tips
1. Use HNSW index for `facts_embedding` (primary search)
2. Consider separate HNSW index for `metadata_embedding` if doing heavy metadata search
3. For very large datasets (>100K cases), use approximate nearest neighbor only
4. Cache frequently-used query embeddings

---

## A/B Testing Recommendations

Test different weight configurations on your use cases:

1. **Baseline**: `α=0.7, β=0.3` (current default)
2. **Fact-heavy**: `α=0.85, β=0.15`
3. **Balanced**: `α=0.5, β=0.5`
4. **Adaptive**: Use query-based weight calculation

**Metrics to track**:
- Precision@K (K=5, 10, 20)
- Mean Reciprocal Rank (MRR)
- User satisfaction (click-through rate)

---

## Summary

✅ **Tier 4 excluded** from fact extraction (saves tokens, avoids empty fields)  
✅ **Metadata embedding** captures procedural info from Phase 1  
✅ **Facts embedding** captures pure case narrative (Tiers 1-3)  
✅ **Hybrid search** combines both with adjustable weights  
✅ **Flexible** - can tune α, β per query type  
✅ **Extensible** - can use other 5 embeddings for specialized searches  

This approach provides the best of both worlds: clean semantic separation with flexible retrieval strategies.
