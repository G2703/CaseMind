"""
Calculate cost estimates for converting files to markdown using LLM pricing.

Reads `price_estimation/summary_pages.json` produced by `inventory_pages.py` and
adds a `models` section with pricing info, estimated cost (INR) and estimated time.

Usage:
  python calculate_costs.py --summary price_estimation/summary_pages.json --usd-to-inr 89

This script embeds a small pricing table (USD per 1M tokens) derived from the
pricing you provided and computes per-model costs.
"""
import argparse
import json
from math import ceil
from pathlib import Path
from datetime import datetime


def estimate_processing_time(total_pages: int, max_concurrent: int = 4, batch_size: int = 20, 
                            avg_processing_time_per_page_sec: float = 2.0) -> int:
    """
    Calculate realistic processing time considering batching and concurrency.
    
    Based on pdf_extractor.py implementation:
    - Each page = 1 API request (page-by-page processing)
    - Pages processed in batches with concurrency control
    - No inter-batch delays (RPM limits are high enough)
    
    Args:
        total_pages: Total number of pages to process
        max_concurrent: Maximum concurrent API requests (default: 4 for Gemini)
        batch_size: Pages processed per batch (default: 20)
        avg_processing_time_per_page_sec: Average API processing time per page
    
    Returns:
        Estimated processing time in minutes
    """
    # Calculate number of batches
    num_batches = ceil(total_pages / batch_size)
    
    # Time per batch: pages in batch / concurrency * avg_time_per_page
    # (concurrency allows parallel processing within batch)
    time_per_batch_sec = ceil(batch_size / max_concurrent) * avg_processing_time_per_page_sec
    
    # Total processing time: batches × time_per_batch (no inter-batch delays)
    total_time_sec = num_batches * time_per_batch_sec
    
    # Convert to minutes
    return ceil(total_time_sec / 60)


def generate_markdown_report(summary: dict, models_out: dict, output_path: Path):
    """Generate a comprehensive markdown report with comparison tables."""
    
    md_lines = []
    md_lines.append("# Cost Estimation Report")
    md_lines.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md_lines.append("\n---\n")
    
    # Inventory Summary
    md_lines.append("## Inventory Summary\n")
    md_lines.append(f"- **Folder**: `{summary.get('folder')}`")
    md_lines.append(f"- **Total Files**: {summary.get('total_files'):,}")
    md_lines.append(f"- **Total Pages**: {summary.get('total_pages'):,}")
    md_lines.append(f"- **Average Pages per File**: {summary.get('avg_pages_per_file', 0):.2f}")
    md_lines.append(f"- **PDF Files Detected**: {summary.get('pdf_detected', 0):,}")
    md_lines.append(f"- **PDF Files Extracted**: {summary.get('pdf_extracted', 0):,}")
    
    computed = summary.get('computed', {})
    md_lines.append(f"\n### Conversion Parameters\n")
    md_lines.append(f"- **Characters per Page**: {summary.get('chars_per_page', 0)}")
    md_lines.append(f"- **Characters per Token**: {summary.get('chars_per_token', 0)}")
    md_lines.append(f"- **Tokens per Page (Output)**: {summary.get('tokens_per_page', 0):.1f}")
    md_lines.append(f"- **Tokens per Image (Input)**: {computed.get('tokens_per_image', 0)}")
    md_lines.append(f"- **Prompt Overhead per Request**: {computed.get('prompt_overhead', 0)} tokens")
    md_lines.append(f"- **Total Requests**: {computed.get('total_requests', 0):,} (1 request per page)")
    md_lines.append(f"- **Total Input Tokens**: {computed.get('total_input_tokens', 0):,}")
    md_lines.append(f"- **Total Output Tokens**: {computed.get('total_output_tokens', 0):,}")
    md_lines.append(f"- **USD to INR Rate**: {computed.get('usd_to_inr', 89)}")
    
    # Model Comparison Table
    md_lines.append("\n---\n")
    md_lines.append("## Model Cost Comparison\n")
    
    # Build comparison table
    md_lines.append("| Model | Input Rate (INR/1k) | Output Rate (INR/1k) | Input Cost (INR) | Output Cost (INR) | **Total Cost (INR)** | Est. Time (min) |")
    md_lines.append("|-------|---------------------|----------------------|------------------|-------------------|----------------------|-----------------|")
    
    for key, model in models_out.items():
        info = model['information']
        est = model['estimates']
        md_lines.append(
            f"| **{model['display']}** | "
            f"{info['input_inr_per_1k']:.4f} | "
            f"{info['output_inr_per_1k']:.4f} | "
            f"{est['input_cost_inr']:,.2f} | "
            f"{est['output_cost_inr']:,.2f} | "
            f"**{est['total_cost_inr']:,.2f}** | "
            f"{est['estimated_time_minutes'] or 'N/A'} |"
        )
    
    # Detailed Model Information
    md_lines.append("\n---\n")
    md_lines.append("## Detailed Model Information\n")
    
    for key, model in models_out.items():
        info = model['information']
        est = model['estimates']
        
        md_lines.append(f"\n### {model['display']}\n")
        
        # Pricing Information
        md_lines.append("**Pricing:**")
        md_lines.append(f"- Input: ${info['input_usd_per_1m']:.2f} per 1M tokens (USD) = ₹{info['input_inr_per_1k']:.4f} per 1k tokens")
        md_lines.append(f"- Output: ${info['output_usd_per_1m']:.2f} per 1M tokens (USD) = ₹{info['output_inr_per_1k']:.4f} per 1k tokens")
        
        # Rate Limits
        md_lines.append(f"\n**Rate Limits:**")
        md_lines.append(f"- Requests per Minute (RPM): {info['rpm'] or 'Not specified'}")
        md_lines.append(f"- Tokens per Minute (TPM): {info['tpm']:,} " if info['tpm'] else "- Tokens per Minute (TPM): Not specified")
        md_lines.append(f"- Requests per Day (RPD): {info['rpd']:,}" if info['rpd'] else "- Requests per Day (RPD): Not specified")
        
        # Cost Breakdown
        md_lines.append(f"\n**Cost Breakdown:**")
        md_lines.append(f"- Total Input Tokens: {est['total_input_tokens']:,}")
        md_lines.append(f"- Total Output Tokens: {est['total_output_tokens']:,}")
        md_lines.append(f"- Input Cost: ₹{est['input_cost_inr']:,.2f}")
        md_lines.append(f"- Output Cost: ₹{est['output_cost_inr']:,.2f}")
        md_lines.append(f"- **Total Cost: ₹{est['total_cost_inr']:,.2f}**")
        
        # Time Information
        md_lines.append(f"\n**Time Estimate:**")
        md_lines.append(f"- Total Requests: {est['total_requests']:,} (1 request per page)")
        md_lines.append(f"- Estimated Time: {est['estimated_time_minutes']} minutes" if est['estimated_time_minutes'] else "- Estimated Time: Not available")
    
    # Cost Ranking
    md_lines.append("\n---\n")
    md_lines.append("## Cost Ranking (Lowest to Highest)\n")
    
    sorted_models = sorted(models_out.items(), key=lambda x: x[1]['estimates']['total_cost_inr'])
    md_lines.append("| Rank | Model | Total Cost (INR) | Time (min) |")
    md_lines.append("|------|-------|------------------|------------|")
    
    for rank, (key, model) in enumerate(sorted_models, 1):
        est = model['estimates']
        md_lines.append(
            f"| {rank} | {model['display']} | "
            f"₹{est['total_cost_inr']:,.2f} | "
            f"{est['estimated_time_minutes'] or 'N/A'} |"
        )
    
    # Formula Documentation
    md_lines.append("\n---\n")
    md_lines.append("## Calculation Formulas\n")
    md_lines.append("\n### Token Calculation (Vision API)\n")
    md_lines.append("```")
    md_lines.append("Input Tokens:")
    md_lines.append("  - Image Tokens = Total Pages × Tokens per Image")
    md_lines.append("  - Prompt Overhead = Total Requests × Prompt Overhead per Request")
    md_lines.append("  - Total Input Tokens = Image Tokens + Prompt Overhead")
    md_lines.append("")
    md_lines.append("Output Tokens:")
    md_lines.append("  - Total Output Tokens = Total Pages × Tokens per Page")
    md_lines.append("")
    md_lines.append("Requests:")
    md_lines.append("  - Total Requests = Total Pages (1 request per page)")
    md_lines.append("```")
    
    md_lines.append("\n### Cost Calculation\n")
    md_lines.append("```")
    md_lines.append("Input Cost (INR) = (Total Input Tokens / 1000) × Input Rate per 1k (INR)")
    md_lines.append("Output Cost (INR) = (Total Output Tokens / 1000) × Output Rate per 1k (INR)")
    md_lines.append("Total Cost (INR) = Input Cost + Output Cost")
    md_lines.append("```")
    
    md_lines.append("\n### Time Estimation\n")
    md_lines.append("```")
    md_lines.append("Based on API rate limits:")
    md_lines.append("  Time by Tokens = ceil((Input Tokens + Output Tokens) / TPM)")
    md_lines.append("  Time by Requests = ceil(Total Requests / RPM)")
    md_lines.append("  Estimated Time = max(Time by Tokens, Time by Requests)")
    md_lines.append("")
    md_lines.append("Note: Actual processing time may vary based on:")
    md_lines.append("  - Network latency")
    md_lines.append("  - API response times")
    md_lines.append("  - Concurrent request limits")
    md_lines.append("  - Batch processing configuration")
    md_lines.append("```")
    
    # Write markdown file
    with output_path.open('w', encoding='utf-8') as f:
        f.write('\n'.join(md_lines))


def usd_per_1m_to_inr_per_1k(usd_per_1m, usd_to_inr_rate):
    # Convert USD per 1M tokens -> INR per 1k tokens
    inr_per_1m = usd_per_1m * usd_to_inr_rate
    return inr_per_1m / 1000.0


def build_pricing_table():
    # Prices taken from the tables you provided. Values are USD per 1M tokens.
    # We'll use the 'Standard' tier where multiple tables exist.
    return {
        'gemini_free': {
            'display': 'Gemini (Free Tier)',
            'input_usd_per_1m': 0.0,
            'output_usd_per_1m': 0.0,
            'rpm': 30,
            'tpm': 125000,
            'rpd': 1000,
        },
        'gemini_tier1': {
            'display': 'Gemini (Tier 1, e.g. Flash)',
            'input_usd_per_1m': 0.30,
            'output_usd_per_1m': 2.50,
            'rpm': 1000,
            'tpm': 1000000,
            'rpd': 10000,
        },
        'gpt_5': {
            'display': 'GPT-5 (standard)',
            'input_usd_per_1m': 1.25,
            'output_usd_per_1m': 10.00,
            'rpm': None,
            'tpm': 1000000,
            'rpd': None,
        },
        'gpt_4_1': {
            'display': 'GPT-4.1 (standard)',
            'input_usd_per_1m': 2.00,
            'output_usd_per_1m': 8.00,
            'rpm': None,
            'tpm': 500000,
            'rpd': None,
        }
    }


def estimate_costs(summary_path: Path, usd_to_inr: float, prompt_overhead: int = 300, context_size: int = 32768, output_multiplier: float = 1.0, tokens_per_image: int = 258, max_concurrent: int = 4, batch_size: int = 20):
    with summary_path.open('r', encoding='utf-8') as fh:
        summary = json.load(fh)

    total_pages = summary.get('total_pages', 0)
    tokens_per_page = summary.get('tokens_per_page') or (summary.get('chars_per_page', 1800) / summary.get('chars_per_token', 4))
    
    # Input: pages are sent as images to vision API
    # Each image consumes tokens_per_image tokens
    total_image_tokens = int(total_pages * tokens_per_image)
    
    # One request per page (no chunking)
    total_requests = int(total_pages)

    # Input tokens: image tokens + prompt overhead per request
    total_input_tokens = total_image_tokens + (total_requests * prompt_overhead)
    
    # Output tokens: markdown text output = pages × tokens_per_page
    total_output_tokens = int(total_pages * tokens_per_page)

    pricing = build_pricing_table()

    models_out = {}

    for key, info in pricing.items():
        in_usd_1m = info['input_usd_per_1m']
        out_usd_1m = info['output_usd_per_1m']

        inr_in_per_1k = usd_per_1m_to_inr_per_1k(in_usd_1m, usd_to_inr)
        inr_out_per_1k = usd_per_1m_to_inr_per_1k(out_usd_1m, usd_to_inr)

        # Use the adjusted token counts
        input_cost_inr = (total_input_tokens / 1000.0) * inr_in_per_1k
        output_cost_inr = (total_output_tokens / 1000.0) * inr_out_per_1k
        total_cost_inr = input_cost_inr + output_cost_inr

        # Time estimates:
        # 1. Based on TPM/RPM limits (theoretical minimum)
        # 2. Based on actual implementation (batched processing with concurrency)
        tpm = info.get('tpm')
        rpm = info.get('rpm')

        time_by_tokens_min = None
        time_by_requests_min = None

        if tpm and tpm > 0:
            # tokens per minute applies to consumed tokens (input + output if sequential)
            # assume token processing is mostly dominated by input+output tokens
            time_by_tokens_min = ceil((total_input_tokens + total_output_tokens) / tpm)

        if rpm and rpm > 0:
            time_by_requests_min = ceil(total_requests / rpm)

        # Time estimate based on rate limits only
        if time_by_tokens_min is not None and time_by_requests_min is not None:
            est_time_min = max(time_by_tokens_min, time_by_requests_min)
        else:
            est_time_min = time_by_tokens_min or time_by_requests_min

        models_out[key] = {
            'display': info.get('display'),
            'information': {
                'input_usd_per_1m': in_usd_1m,
                'output_usd_per_1m': out_usd_1m,
                'input_inr_per_1k': round(inr_in_per_1k, 6),
                'output_inr_per_1k': round(inr_out_per_1k, 6),
                'rpm': rpm,
                'tpm': tpm,
                'rpd': info.get('rpd')
            },
            'estimates': {
                'total_input_tokens': total_input_tokens,
                'total_output_tokens': total_output_tokens,
                'total_requests': total_requests,
                'input_cost_inr': round(input_cost_inr, 2),
                'output_cost_inr': round(output_cost_inr, 2),
                'total_cost_inr': round(total_cost_inr, 2),
                'estimated_time_minutes': est_time_min
            }
        }

    # attach to summary and write out
    summary['models'] = models_out
    summary['computed'] = {
        'total_pages': total_pages,
        'tokens_per_image': tokens_per_image,
        'tokens_per_page': tokens_per_page,
        'total_requests': total_requests,
        'total_input_tokens': total_input_tokens,
        'total_output_tokens': total_output_tokens,
        'prompt_overhead': prompt_overhead,
        'usd_to_inr': usd_to_inr
    }

    # Write JSON for programmatic use
    json_path = summary_path
    with json_path.open('w', encoding='utf-8') as fh:
        json.dump(summary, fh, indent=2)
    
    # Generate markdown report
    md_path = summary_path.parent / 'cost_estimation_report.md'
    generate_markdown_report(summary, models_out, md_path)

    # print a concise terminal table
    print('\nInventory Summary:')
    print(f"Folder: {summary.get('folder')}")
    print(f"Total files: {summary.get('total_files')}")
    print(f"Total pages (estimated): {summary.get('total_pages')}")
    print(f"Average pages per file: {summary.get('avg_pages_per_file'):.2f}")
    print(f"Chars per page (assumed): {summary.get('chars_per_page')}")
    print(f"Chars per token (assumed): {summary.get('chars_per_token')}")
    print(f"Tokens per page (output text): {tokens_per_page:.1f}")
    print(f"Tokens per image (input): {tokens_per_image}")
    print(f"Total requests: {total_requests} (1 request per page)\n")

    for k, v in models_out.items():
        info = v['information']
        est = v['estimates']
        print(f"{v['display']}:")
        print(f" Information - input_rate(INR/1k): {info['input_inr_per_1k']}, output_rate(INR/1k): {info['output_inr_per_1k']}, rpm: {info['rpm']}, tpm: {info['tpm']}, rpd: {info['rpd']}")
        print(f" Estimated cost (INR): {est['total_cost_inr']:,} (input: {est['input_cost_inr']:,}, output: {est['output_cost_inr']:,})")
        print(f" Total requests: {est['total_requests']:,}")
        print(f" Estimated time: {est['estimated_time_minutes']} minutes" if est['estimated_time_minutes'] else " Estimated time: Not available")
        print()

    print(f"\nJSON summary written to: {json_path}")
    print(f"Markdown report written to: {md_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--summary', default='price_estimation/summary_pages.json', help='Path to inventory summary JSON')
    parser.add_argument('--usd-to-inr', '--usd_to_inr', default=89.0, type=float, help='USD to INR conversion rate')
    parser.add_argument('--prompt-overhead', '--prompt_overhead', default=300, type=int, help='Prompt/system tokens per request')
    parser.add_argument('--context-size', '--context_size', default=32768, type=int, help='Model context window size (deprecated)')
    parser.add_argument('--output-multiplier', '--output_multiplier', default=1.0, type=float, help='Output token expansion/compression multiplier (deprecated)')
    parser.add_argument('--tokens-per-image', '--tokens_per_image', default=258, type=int, help='Tokens consumed per image (vision API billing)')
    parser.add_argument('--max-concurrent', '--max_concurrent', default=4, type=int, help='Max concurrent API requests (from pdf_extractor.py, default: 4)')
    parser.add_argument('--batch-size', '--batch_size', default=20, type=int, help='Pages per batch before delay (from pdf_extractor.py, default: 20)')
    args = parser.parse_args()

    estimate_costs(Path(args.summary), args.usd_to_inr, args.prompt_overhead, args.context_size, args.output_multiplier, args.tokens_per_image, args.max_concurrent, args.batch_size)


if __name__ == '__main__':
    main()
