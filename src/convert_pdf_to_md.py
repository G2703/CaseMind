"""
PDF to Markdown Converter for Legal Cases
Converts PDF files to readable markdown format for text processing.
"""
import fitz  # PyMuPDF
import os
import logging
from pathlib import Path
import re
from typing import Optional

class PDFToMarkdownConverter:
    """Converts PDF files to markdown format with proper text cleaning."""
    
    def __init__(self, config: Optional[dict] = None):
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        self.save_markdown = self.config.get('processing_settings', {}).get('save_markdown_files', False)
        self.markdown_dir = self.config.get('processing_settings', {}).get('markdown_output_dir', 'cases/markdown')
        
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extract text from PDF file using PyMuPDF.
        
        Args:
            pdf_path (str): Path to the PDF file
            
        Returns:
            str: Extracted text content
        """
        try:
            doc = fitz.open(pdf_path)
            text_content = []
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                text = page.get_text()
                
                # Add page separator for better structure
                if page_num > 0:
                    text_content.append(f"\n\n--- Page {page_num + 1} ---\n")
                
                text_content.append(text)
            
            doc.close()
            extracted_text = "".join(text_content)
            
            # Save markdown file if enabled
            if self.save_markdown:
                self._save_markdown_file(pdf_path, extracted_text)
            
            return extracted_text
            
        except Exception as e:
            self.logger.error(f"Error extracting text from PDF {pdf_path}: {e}")
            raise
    
    def clean_text(self, text: str) -> str:
        """
        Clean extracted text for better readability.
        
        Args:
            text (str): Raw text from PDF
            
        Returns:
            str: Cleaned text
        """
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
        
        # Fix line breaks in middle of sentences
        text = re.sub(r'([a-z])\n([a-z])', r'\1 \2', text)
        
        # Remove excessive spaces
        text = re.sub(r' +', ' ', text)
        
        # Remove trailing whitespace from lines
        text = '\n'.join(line.strip() for line in text.split('\n'))
        
        return text.strip()
    
    def format_as_markdown(self, text: str, case_title: Optional[str] = None) -> str:
        """
        Format text as markdown with proper headers and structure.
        
        Args:
            text (str): Cleaned text content
            case_title (str, optional): Case title for header
            
        Returns:
            str: Formatted markdown content
        """
        markdown_content = []
        
        # Add header if case title is provided
        if case_title:
            markdown_content.append(f"# {case_title}\n")
        else:
            markdown_content.append("# Legal Case Document\n")
        
        # Add metadata section
        markdown_content.append("## Case Information\n")
        
        # Split text into sections based on common legal document patterns
        sections = self._identify_sections(text)
        
        for section_title, section_content in sections:
            if section_content.strip():
                markdown_content.append(f"## {section_title}\n")
                markdown_content.append(f"{section_content}\n")
        
        return "\n".join(markdown_content)
    
    def _identify_sections(self, text: str) -> list:
        """
        Identify common sections in legal documents.
        
        Args:
            text (str): Document text
            
        Returns:
            list: List of (section_title, section_content) tuples
        """
        sections = []
        
        # Common legal document section patterns
        section_patterns = [
            (r'CORAM\s*:?', 'Coram'),
            (r'PRESENT\s*:?', 'Present'),
            (r'JUDGMENT\s*:?', 'Judgment'),
            (r'ORDER\s*:?', 'Order'),
            (r'FACTS\s*:?', 'Facts'),
            (r'HELD\s*:?', 'Held'),
            (r'RATIO\s*:?', 'Ratio'),
            (r'CONCLUSION\s*:?', 'Conclusion'),
            (r'APPEAL\s*:?', 'Appeal Details'),
        ]
        
        # If no clear sections found, treat as single content block
        found_sections = False
        current_section = "Document Content"
        current_content = []
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                current_content.append('')
                continue
                
            # Check if line matches any section pattern
            section_found = False
            for pattern, section_name in section_patterns:
                if re.match(pattern, line, re.IGNORECASE):
                    # Save previous section
                    if current_content:
                        sections.append((current_section, '\n'.join(current_content)))
                    
                    # Start new section
                    current_section = section_name
                    current_content = []
                    found_sections = True
                    section_found = True
                    break
            
            if not section_found:
                current_content.append(line)
        
        # Add the last section
        if current_content:
            sections.append((current_section, '\n'.join(current_content)))
        
        # If no sections were identified, return as single block
        if not found_sections:
            sections = [("Document Content", text)]
        
        return sections
    
    def convert_pdf_to_markdown(self, pdf_path: str, output_dir: str) -> str:
        """
        Convert PDF file to markdown and save to output directory.
        
        Args:
            pdf_path (str): Path to input PDF file
            output_dir (str): Directory to save markdown file
            
        Returns:
            str: Path to created markdown file
        """
        try:
            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)
            
            # Extract filename without extension
            pdf_name = Path(pdf_path).stem
            
            # Extract text from PDF
            self.logger.info(f"Extracting text from {pdf_path}")
            raw_text = self.extract_text_from_pdf(pdf_path)
            
            # Clean the text
            cleaned_text = self.clean_text(raw_text)
            
            # Format as markdown
            markdown_content = self.format_as_markdown(cleaned_text, pdf_name)
            
            # Save to markdown file
            markdown_path = os.path.join(output_dir, f"{pdf_name}.md")
            with open(markdown_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            self.logger.info(f"Converted PDF to markdown: {markdown_path}")
            return markdown_path
            
        except Exception as e:
            self.logger.error(f"Error converting PDF to markdown: {e}")
            raise
    
    def _save_markdown_file(self, pdf_path: str, extracted_text: str) -> None:
        """
        Save extracted text as markdown file.
        
        Args:
            pdf_path (str): Original PDF file path
            extracted_text (str): Extracted text content
        """
        try:
            # Create markdown directory if it doesn't exist
            os.makedirs(self.markdown_dir, exist_ok=True)
            
            # Get PDF filename without extension
            pdf_name = Path(pdf_path).stem
            
            # Clean the text
            cleaned_text = self.clean_text(extracted_text)
            
            # Format as markdown with case title
            markdown_content = self.format_as_markdown(cleaned_text, pdf_name)
            
            # Create markdown file path
            markdown_path = os.path.join(self.markdown_dir, f"{pdf_name}.md")
            
            # Save markdown file
            with open(markdown_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            self.logger.info(f"Saved markdown file: {markdown_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving markdown file for {pdf_path}: {e}")
            # Don't raise exception here as this is optional functionality

def main():
    """Example usage of PDF to Markdown converter."""
    converter = PDFToMarkdownConverter()
    
    # Example conversion
    pdf_path = "cases/input_files/sample_case.pdf"
    output_dir = "cases/processed"
    
    if os.path.exists(pdf_path):
        markdown_path = converter.convert_pdf_to_markdown(pdf_path, output_dir)
        print(f"Converted: {pdf_path} -> {markdown_path}")
    else:
        print(f"PDF file not found: {pdf_path}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()