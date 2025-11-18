# Cost Estimation Report

Generated: 2025-11-18 12:31:33

---

## Inventory Summary

- **Folder**: `cases\input_files`
- **Total Files**: 1,574
- **Total Pages**: 143,967
- **Average Pages per File**: 91.47
- **PDF Files Detected**: 1,509
- **PDF Files Extracted**: 1,509

### Conversion Parameters

- **Characters per Page**: 500
- **Characters per Token**: 4.0
- **Tokens per Page (Output)**: 125.0
- **Tokens per Image (Input)**: 258
- **Prompt Overhead per Request**: 300 tokens
- **Total Requests**: 143,967 (1 request per page)
- **Total Input Tokens**: 80,333,586
- **Total Output Tokens**: 17,995,875
- **USD to INR Rate**: 89.0

---

## Model Cost Comparison

| Model | Input Rate (INR/1k) | Output Rate (INR/1k) | Input Cost (INR) | Output Cost (INR) | **Total Cost (INR)** | Est. Time (min) |
|-------|---------------------|----------------------|------------------|-------------------|----------------------|-----------------|
| **Gemini (Free Tier)** | 0.0000 | 0.0000 | 0.00 | 0.00 | **0.00** | 4799 |
| **Gemini (Tier 1, e.g. Flash)** | 0.0267 | 0.2225 | 2,144.91 | 4,004.08 | **6,148.99** | 144 |
| **GPT-5 (standard)** | 0.1113 | 0.8900 | 8,937.11 | 16,016.33 | **24,953.44** | 99 |
| **GPT-4.1 (standard)** | 0.1780 | 0.7120 | 14,299.38 | 12,813.06 | **27,112.44** | 197 |

---

## Detailed Model Information


### Gemini (Free Tier)

**Pricing:**
- Input: $0.00 per 1M tokens (USD) = ₹0.0000 per 1k tokens
- Output: $0.00 per 1M tokens (USD) = ₹0.0000 per 1k tokens

**Rate Limits:**
- Requests per Minute (RPM): 30
- Tokens per Minute (TPM): 125,000 
- Requests per Day (RPD): 1,000

**Cost Breakdown:**
- Total Input Tokens: 80,333,586
- Total Output Tokens: 17,995,875
- Input Cost: ₹0.00
- Output Cost: ₹0.00
- **Total Cost: ₹0.00**

**Time Estimate:**
- Total Requests: 143,967 (1 request per page)
- Estimated Time: 4799 minutes

### Gemini (Tier 1, e.g. Flash)

**Pricing:**
- Input: $0.30 per 1M tokens (USD) = ₹0.0267 per 1k tokens
- Output: $2.50 per 1M tokens (USD) = ₹0.2225 per 1k tokens

**Rate Limits:**
- Requests per Minute (RPM): 1000
- Tokens per Minute (TPM): 1,000,000 
- Requests per Day (RPD): 10,000

**Cost Breakdown:**
- Total Input Tokens: 80,333,586
- Total Output Tokens: 17,995,875
- Input Cost: ₹2,144.91
- Output Cost: ₹4,004.08
- **Total Cost: ₹6,148.99**

**Time Estimate:**
- Total Requests: 143,967 (1 request per page)
- Estimated Time: 144 minutes

### GPT-5 (standard)

**Pricing:**
- Input: $1.25 per 1M tokens (USD) = ₹0.1113 per 1k tokens
- Output: $10.00 per 1M tokens (USD) = ₹0.8900 per 1k tokens

**Rate Limits:**
- Requests per Minute (RPM): Not specified
- Tokens per Minute (TPM): 1,000,000 
- Requests per Day (RPD): Not specified

**Cost Breakdown:**
- Total Input Tokens: 80,333,586
- Total Output Tokens: 17,995,875
- Input Cost: ₹8,937.11
- Output Cost: ₹16,016.33
- **Total Cost: ₹24,953.44**

**Time Estimate:**
- Total Requests: 143,967 (1 request per page)
- Estimated Time: 99 minutes

### GPT-4.1 (standard)

**Pricing:**
- Input: $2.00 per 1M tokens (USD) = ₹0.1780 per 1k tokens
- Output: $8.00 per 1M tokens (USD) = ₹0.7120 per 1k tokens

**Rate Limits:**
- Requests per Minute (RPM): Not specified
- Tokens per Minute (TPM): 500,000 
- Requests per Day (RPD): Not specified

**Cost Breakdown:**
- Total Input Tokens: 80,333,586
- Total Output Tokens: 17,995,875
- Input Cost: ₹14,299.38
- Output Cost: ₹12,813.06
- **Total Cost: ₹27,112.44**

**Time Estimate:**
- Total Requests: 143,967 (1 request per page)
- Estimated Time: 197 minutes

---

## Cost Ranking (Lowest to Highest)

| Rank | Model | Total Cost (INR) | Time (min) |
|------|-------|------------------|------------|
| 1 | Gemini (Free Tier) | ₹0.00 | 4799 |
| 2 | Gemini (Tier 1, e.g. Flash) | ₹6,148.99 | 144 |
| 3 | GPT-5 (standard) | ₹24,953.44 | 99 |
| 4 | GPT-4.1 (standard) | ₹27,112.44 | 197 |

---

## Calculation Formulas


### Token Calculation (Vision API)

```
Input Tokens:
  - Image Tokens = Total Pages × Tokens per Image
  - Prompt Overhead = Total Requests × Prompt Overhead per Request
  - Total Input Tokens = Image Tokens + Prompt Overhead

Output Tokens:
  - Total Output Tokens = Total Pages × Tokens per Page

Requests:
  - Total Requests = Total Pages (1 request per page)
```

### Cost Calculation

```
Input Cost (INR) = (Total Input Tokens / 1000) × Input Rate per 1k (INR)
Output Cost (INR) = (Total Output Tokens / 1000) × Output Rate per 1k (INR)
Total Cost (INR) = Input Cost + Output Cost
```

### Time Estimation

```
Based on API rate limits:
  Time by Tokens = ceil((Input Tokens + Output Tokens) / TPM)
  Time by Requests = ceil(Total Requests / RPM)
  Estimated Time = max(Time by Tokens, Time by Requests)

Note: Actual processing time may vary based on:
  - Network latency
  - API response times
  - Concurrent request limits
  - Batch processing configuration
```