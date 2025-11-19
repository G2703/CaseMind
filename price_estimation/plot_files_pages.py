"""
Plot file distribution by page count and analyze PDF types (text-based vs image-based).

Usage:
  python plot_files_pages.py --folder cases/input_files
"""
import os
import argparse
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import fitz  # PyMuPDF


def analyze_pdf(path: Path):
    """
    Analyze a PDF file using PyMuPDF.
    
    Returns:
        dict with keys: pages (int), pdf_type ('text' or 'image'), error (str or None)
    """
    try:
        doc = fitz.open(str(path))
        num_pages = len(doc)
        
        # Check first page for text content
        if num_pages > 0:
            first_page = doc.load_page(0)
            text = first_page.get_text()
            pdf_type = 'text' if len(text.strip()) > 0 else 'image'
        else:
            pdf_type = 'unknown'
        
        doc.close()
        return {
            'pages': num_pages,
            'pdf_type': pdf_type,
            'error': None
        }
    except Exception as e:
        return {
            'pages': None,
            'pdf_type': 'error',
            'error': str(e)
        }


def collect_file_data(folder: str):
    """Collect PDF file data using PyMuPDF."""
    p = Path(folder)
    pdf_files = []
    
    # Collect all PDF files
    for root, dirs, filenames in os.walk(p):
        for fn in filenames:
            filepath = Path(root) / fn
            if filepath.suffix.lower() == '.pdf':
                pdf_files.append(filepath)
    
    file_data = []
    
    print(f"Analyzing {len(pdf_files)} PDF files...")
    for i, f in enumerate(pdf_files, 1):
        if i % 100 == 0:
            print(f"  Processed {i}/{len(pdf_files)} files...")
        
        size_bytes = f.stat().st_size
        analysis = analyze_pdf(f)
        
        file_data.append({
            'sr_no': i,
            'name': f.name,
            'path': str(f),
            'file_size_bytes': size_bytes,
            'file_size_mb': round(size_bytes / (1024 * 1024), 2),
            'pages': analysis['pages'] if analysis['pages'] is not None else 0,
            'type': analysis['pdf_type'],
            'error': analysis['error']
        })
    
    return file_data


def plot_files_pages(file_data, output_path='price_estimation/files_pages_plot.png'):
    """Create visualization of files vs pages."""
    
    # Create DataFrame
    df = pd.DataFrame(file_data)
    
    # Save DataFrame to CSV
    csv_path = output_path.replace('_plot.png', '_data.csv')
    df.to_csv(csv_path, index=False)
    print(f"\nDataFrame saved to: {csv_path}")
    
    # Filter out error files for plotting
    df_valid = df[df['pages'] > 0].copy()
    
    # Sort by page count for better visualization
    df_sorted = df_valid.sort_values('pages')
    
    pages = df_sorted['pages'].values
    
    # Create figure with larger size
    plt.figure(figsize=(20, 8))
    
    # Create bar plot with color coding for PDF type
    colors = []
    for pdf_type in df_sorted['type']:
        if pdf_type == 'text':
            colors.append('steelblue')
        elif pdf_type == 'image':
            colors.append('crimson')
        else:
            colors.append('gray')
    
    bars = plt.bar(range(len(pages)), pages, color=colors, alpha=0.7, edgecolor='navy')
    
    plt.xlabel('PDF Files', fontsize=12, fontweight='bold')
    plt.ylabel('Number of Pages', fontsize=12, fontweight='bold')
    
    # Count by type
    text_count = len(df_valid[df_valid['type'] == 'text'])
    image_count = len(df_valid[df_valid['type'] == 'image'])
    error_count = len(df[df['type'] == 'error'])
    
    plt.title(f'PDF File Distribution by Page Count\n'
              f'Total PDFs: {len(df)} | Text-based: {text_count} | Image-based: {image_count} | Errors: {error_count}\n'
              f'Total Pages: {df_valid["pages"].sum():,} | Avg Pages: {df_valid["pages"].mean():.1f}', 
              fontsize=14, fontweight='bold')
    
    # Add grid for better readability
    plt.grid(axis='y', alpha=0.3, linestyle='--')
    
    # Add legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='steelblue', alpha=0.7, label=f'Text-based ({text_count})'),
        Patch(facecolor='crimson', alpha=0.7, label=f'Image-based ({image_count})')
    ]
    plt.legend(handles=legend_elements, loc='upper left', fontsize=10)
    
    # Add statistics box
    stats_text = f'Min: {df_valid["pages"].min()} pages\nMax: {df_valid["pages"].max()} pages\nMedian: {df_valid["pages"].median():.0f} pages\nStd Dev: {df_valid["pages"].std():.1f}'
    plt.text(0.98, 0.97, stats_text, transform=plt.gca().transAxes,
             fontsize=10, verticalalignment='top', horizontalalignment='right',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    # Remove x-axis labels (too many files to show individual names)
    plt.xticks([])
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"Plot saved to: {output_path}")
    
    # Create histogram
    plt.figure(figsize=(12, 6))
    plt.hist(df_valid[df_valid['type'] == 'text']['pages'], bins=50, 
             color='steelblue', alpha=0.6, edgecolor='navy', label=f'Text-based ({text_count})')
    plt.hist(df_valid[df_valid['type'] == 'image']['pages'], bins=50, 
             color='crimson', alpha=0.6, edgecolor='darkred', label=f'Image-based ({image_count})')
    
    plt.xlabel('Number of Pages', fontsize=12, fontweight='bold')
    plt.ylabel('Frequency (Number of Files)', fontsize=12, fontweight='bold')
    plt.title(f'Distribution of Page Counts Across PDF Files\nTotal Files: {len(df_valid)}', 
              fontsize=14, fontweight='bold')
    plt.legend(loc='upper right')
    plt.grid(axis='y', alpha=0.3, linestyle='--')
    
    histogram_path = output_path.replace('_plot.png', '_histogram.png')
    plt.tight_layout()
    plt.savefig(histogram_path, dpi=150, bbox_inches='tight')
    print(f"Histogram saved to: {histogram_path}")
    
    # Print summary statistics
    print("\n" + "="*80)
    print("SUMMARY STATISTICS")
    print("="*80)
    print(f"\nTotal PDF files analyzed: {len(df)}")
    print(f"  - Text-based PDFs: {text_count} ({text_count/len(df)*100:.1f}%)")
    print(f"  - Image-based PDFs: {image_count} ({image_count/len(df)*100:.1f}%)")
    print(f"  - Errors: {error_count}")
    
    print(f"\nTotal pages: {df_valid['pages'].sum():,}")
    print(f"Average pages per file: {df_valid['pages'].mean():.1f}")
    print(f"Median pages per file: {df_valid['pages'].median():.0f}")
    print(f"Min pages: {df_valid['pages'].min()}")
    print(f"Max pages: {df_valid['pages'].max()}")
    
    print(f"\nTotal file size: {df['file_size_mb'].sum():.2f} MB")
    print(f"Average file size: {df['file_size_mb'].mean():.2f} MB")
    
    # Print top 10 files by page count
    print("\n" + "="*80)
    print("TOP 10 FILES BY PAGE COUNT")
    print("="*80)
    top_files = df.nlargest(10, 'pages')
    for _, row in top_files.iterrows():
        print(f"{row['sr_no']:4d}. {row['name'][:50]:50s} - {row['pages']:5d} pages ({row['type']:5s}) - {row['file_size_mb']:6.2f} MB")
    
    # Print type breakdown
    print("\n" + "="*80)
    print("PDF TYPE BREAKDOWN")
    print("="*80)
    print(f"\nText-based PDFs:")
    text_df = df_valid[df_valid['type'] == 'text']
    if len(text_df) > 0:
        print(f"  Total: {len(text_df)}")
        print(f"  Total pages: {text_df['pages'].sum():,}")
        print(f"  Avg pages: {text_df['pages'].mean():.1f}")
        print(f"  Total size: {text_df['file_size_mb'].sum():.2f} MB")
    
    print(f"\nImage-based PDFs:")
    image_df = df_valid[df_valid['type'] == 'image']
    if len(image_df) > 0:
        print(f"  Total: {len(image_df)}")
        print(f"  Total pages: {image_df['pages'].sum():,}")
        print(f"  Avg pages: {image_df['pages'].mean():.1f}")
        print(f"  Total size: {image_df['file_size_mb'].sum():.2f} MB")
    
    print("\n" + "="*80)


def main():
    parser = argparse.ArgumentParser(description='Analyze PDF files and plot distribution by page count')
    parser.add_argument('--folder', default='cases/input_files', help='Target folder to analyze')
    parser.add_argument('--output', default='price_estimation/files_pages_plot.png', 
                       help='Output plot file path')
    
    args = parser.parse_args()
    
    print(f"Analyzing PDF files in: {args.folder}")
    file_data = collect_file_data(args.folder)
    
    if not file_data:
        print("No PDF files found!")
        return
    
    print(f"\nCreating plots and DataFrame...")
    plot_files_pages(file_data, args.output)
    
    print("\n✓ Analysis complete!")


if __name__ == '__main__':
    main()
