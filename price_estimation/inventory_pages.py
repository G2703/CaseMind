"""
Inventory script for estimating average pages per file and token-related defaults.

Usage:
  python inventory_pages.py --folder cases/input_files --default-pages 5 --chars-per-page 1800 --chars-per-token 4

This script:
- Walks the target folder recursively
- Reads PDF page counts (PyPDF2) when available
- Uses `--default-pages` for non-PDF files or when page extraction fails
- Computes and prints counts and averages
- Writes a summary JSON to `price_estimation/summary_pages.json`

"""
import os
import argparse
import json
from pathlib import Path

try:
    from PyPDF2 import PdfReader
    HAS_PYPDF2 = True
except Exception:
    HAS_PYPDF2 = False

try:
    import docx
    HAS_DOCX = True
except Exception:
    HAS_DOCX = False

def get_pdf_page_count(path: Path) -> int:
    if not HAS_PYPDF2:
        return None
    try:
        reader = PdfReader(str(path))
        return len(reader.pages)
    except Exception:
        return None


def get_docx_text_chars(path: Path) -> int:
    if not HAS_DOCX:
        return None
    try:
        doc = docx.Document(str(path))
        full = []
        for p in doc.paragraphs:
            full.append(p.text)
        text = "\n".join(full)
        return len(text)
    except Exception:
        return None


def get_text_file_chars(path: Path) -> int:
    try:
        with path.open('r', encoding='utf-8', errors='ignore') as fh:
            txt = fh.read()
            return len(txt)
    except Exception:
        return None


def inventory(folder: str, default_pages: int, chars_per_page: int):
    p = Path(folder)
    files = []
    for root, dirs, filenames in os.walk(p):
        for fn in filenames:
            files.append(Path(root) / fn)

    total_files = len(files)
    total_pages = 0
    per_file_pages = []
    pdf_detected = 0
    pdf_extracted = 0
    docx_extracted = 0
    text_extracted = 0

    for f in files:
        suffix = f.suffix.lower()
        size_bytes = f.stat().st_size
        pages = None
        method = 'fallback'
        raw_chars = None

        if suffix == '.pdf':
            pdf_detected += 1
            pages = get_pdf_page_count(f)
            if pages is not None:
                method = 'pdf-metadata'
                pdf_extracted += 1
        elif suffix == '.docx':
            chars = get_docx_text_chars(f)
            if chars is not None:
                raw_chars = chars
                pages = max(1, int((chars + chars_per_page - 1) / chars_per_page))
                method = 'docx-text'
                docx_extracted += 1
        elif suffix in ('.txt', '.md'):
            chars = get_text_file_chars(f)
            if chars is not None:
                raw_chars = chars
                pages = max(1, int((chars + chars_per_page - 1) / chars_per_page))
                method = 'text'
                text_extracted += 1

        if pages is None:
            # fallback: estimate pages from file size heuristics or default
            # simple heuristic: assume average bytes per page == chars_per_page * 1 (approx 1 byte per char)
            est_pages = max(1, int((size_bytes + chars_per_page - 1) / chars_per_page))
            pages = est_pages if size_bytes > 0 else default_pages

        per_file_pages.append({
            'path': str(f),
            'pages': pages,
            'size_bytes': size_bytes,
            'method': method,
            'raw_chars': raw_chars
        })
        total_pages += pages

    avg_pages_per_file = (total_pages / total_files) if total_files else 0

    return {
        'folder': str(p),
        'total_files': total_files,
        'total_pages': total_pages,
        'avg_pages_per_file': avg_pages_per_file,
        'pdf_detected': pdf_detected,
        'pdf_extracted': pdf_extracted,
        'docx_extracted': docx_extracted,
        'text_extracted': text_extracted
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--folder', '--folder_path', default='cases/input_files', help='Target folder to inventory')
    parser.add_argument('--default-pages', '--default_pages', default=5, type=int, help='Default pages per non-PDF file or when page extraction fails')
    parser.add_argument('--chars-per-page', '--chars_per_page', default=1800, type=int, help='Assumed average characters per page')
    parser.add_argument('--chars-per-token', '--chars_per_token', default=4, type=float, help='Heuristic: characters per token')
    parser.add_argument('--out', '--out_path', default='price_estimation/summary_pages.json', help='Summary JSON output path')

    args = parser.parse_args()

    summary = inventory(args.folder, args.default_pages, args.chars_per_page)
    summary['chars_per_page'] = args.chars_per_page
    summary['chars_per_token'] = args.chars_per_token
    summary['tokens_per_page'] = args.chars_per_page / args.chars_per_token if args.chars_per_token else None

    # print summary
    print('\nInventory Summary:')
    print(f"Folder: {summary['folder']}")
    print(f"Total files: {summary['total_files']}")
    print(f"Total pages (estimated): {summary['total_pages']}")
    print(f"Average pages per file: {summary['avg_pages_per_file']:.2f}")
    print(f"Chars per page (assumed): {summary['chars_per_page']}")
    print(f"Chars per token (assumed): {summary['chars_per_token']}")
    print(f"Tokens per page (estimated): {summary['tokens_per_page']:.1f}\n")

    # write JSON
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open('w', encoding='utf-8') as fh:
        json.dump(summary, fh, indent=2)

    print(f"Summary written to: {out_path}")


if __name__ == '__main__':
    main()
