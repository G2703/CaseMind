#!/usr/bin/env python3
"""
Test script to debug PDF content extraction.
"""
import os
import sys
sys.path.append('src/bg_creation')

from convert_pdf_to_md import PDFToMarkdownConverter

def test_pdf_extraction():
    """Test PDF to markdown conversion."""
    
    pdf_path = "cases/input_files/Cases/Dacoity/HC/Abdulla Momin Vs St of Mah.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"PDF file not found: {pdf_path}")
        return
        
    print(f"Testing PDF extraction for: {pdf_path}")
    
    # Initialize converter
    converter = PDFToMarkdownConverter()
    
    # Convert PDF to markdown
    try:
        output_dir = "cases/markdown"
        os.makedirs(output_dir, exist_ok=True)
        markdown_path = converter.convert_pdf_to_markdown(pdf_path, output_dir)
        print(f"✓ Converted to markdown: {markdown_path}")
        
        # Read the markdown content
        if os.path.exists(markdown_path):
            with open(markdown_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            print(f"Markdown content length: {len(content)} characters")
            print("\nFirst 500 characters:")
            print("=" * 50)
            print(content[:500])
            print("=" * 50)
            
            if len(content.strip()) == 0:
                print("✗ Warning: Markdown content is empty!")
            else:
                print("✓ Markdown content extracted successfully")
                
        else:
            print(f"✗ Markdown file not created: {markdown_path}")
            
    except Exception as e:
        print(f"✗ Error during conversion: {e}")

if __name__ == "__main__":
    test_pdf_extraction()