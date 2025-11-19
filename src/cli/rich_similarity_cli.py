"""
Rich CLI for CaseMind Similarity Analyzer
A professional command-line interface with modern gradient design
"""

import os
import sys
import time
from typing import Dict, List, Tuple, Any
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.prompt import Prompt
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.align import Align

from src.similarity_pipeline.similarity_search_pipeline import SimilarityCaseSearchPipeline
from dotenv import load_dotenv
load_dotenv()

class RichSimilarityCLI:
    """Professional CLI for legal case similarity analysis with modern gradient design."""
    
    def __init__(self, log_dir: str = "logs"):
        """Initialize the Rich CLI."""
        self.console = Console()
        self.log_dir = log_dir
        
        # Formal professional color scheme optimized for dark terminal backgrounds
        self.colors = {
            'primary': "#c2edff",      # Bright blue - professional yet visible on dark
            'secondary': "#dbcffe",    # Light purple - sophisticated and distinct
            'success': '#34d399',      # Bright green - positive and clearly visible
            'warning': '#fbbf24',      # Bright yellow - attention-grabbing but professional
            'error': '#f87171',        # Bright red - clear error indication
            'info': "#61a8ff",         # Bright cyan - informative and trustworthy
            'text': '#f8fafc',         # Pure white - maximum contrast on dark
            'muted': '#9ca3af',        # Light gray - visible but subtle on dark
            'accent': '#10b981',       # Bright emerald - modern and professional
            'gold': '#f59e0b',         # Bright gold - premium highlighting
            'purple': '#8b5cf6',       # Medium purple - elegant and visible
            'rose': '#fb7185',         # Bright rose - elegant accent
            'highlight': '#ddd6fe',    # Light lavender - highlighting without being harsh
        }
        
        # Ensure log directory exists
        os.makedirs(log_dir, exist_ok=True)
    
    def show_welcome_screen(self):
        """Display professional welcome screen with ASCII art logo."""
        self.console.clear()
        
        # ASCII art logo with updated structure - center aligned
        logo = Text()
        logo.append("╔═════════════════════════════════════════════════════════════════════════════════════════════════════════╗\n", style=self.colors['primary'])
        logo.append("║                                                                                                         ║\n", style=self.colors['primary'])
        logo.append("║                                                                                                         ║\n", style=self.colors['primary'])
        logo.append("║                     ██████╗ █████╗ ███████╗███████╗███╗   ███╗██╗███╗   ██╗██████╗                      ║\n", style=f"bold {self.colors['primary']}")
        logo.append("║                    ██╔════╝██╔══██╗██╔════╝██╔════╝████╗ ████║██║████╗  ██║██╔══██╗                     ║\n", style=f"bold {self.colors['primary']}")
        logo.append("║                    ██║     ███████║███████╗█████╗  ██╔████╔██║██║██╔██╗ ██║██║  ██║                     ║\n", style=f"bold {self.colors['primary']}")
        logo.append("║                    ██║     ██╔══██║╚════██║██╔══╝  ██║╚██╔╝██║██║██║╚██╗██║██║  ██║                     ║\n", style=f"bold {self.colors['primary']}")
        logo.append("║                    ╚██████╗██║  ██║███████║███████╗██║ ╚═╝ ██║██║██║ ╚████║██████╔╝                     ║\n", style=f"bold {self.colors['primary']}")
        logo.append("║                     ╚═════╝╚═╝  ╚═╝╚══════╝╚══════╝╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝╚═════╝                      ║\n", style=f"bold {self.colors['primary']}")
        logo.append("║                                                                                                         ║\n", style=self.colors['primary'])
        logo.append("║                                            Similarity Analyzer                                          ║\n", style=self.colors['secondary'])
        logo.append("║                              AI-Powered Legal Case Similarity Search & Analysis                         ║\n", style=self.colors['secondary'])
        logo.append("║                                                                                                         ║\n", style=self.colors['primary'])
        logo.append("║               ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━            ║\n", style=self.colors['primary'])
        logo.append("║                                                  Features                                               ║\n", style=self.colors['text'])
        logo.append("║                                                                                                         ║\n", style=f"bold {self.colors['primary']}")
        logo.append("║  • Advanced semantic similarity using embeddings         • Cross-encoder re-ranking for precision       ║\n", style=self.colors['info'])
        logo.append("║   • Intelligent threshold-based filtering                  • Comprehensive metadata extraction          ║\n", style=self.colors['info'])
        logo.append("║                                                                                                         ║\n", style=self.colors['primary'])
        logo.append("╚═════════════════════════════════════════════════════════════════════════════════════════════════════════╝", style=self.colors['primary'])
        
        self.console.print(Align.center(logo))
        self.console.print()
    
    def get_file_input(self) -> str:
        """Get PDF file path from user with validation."""
        while True:
            self.console.print(
                Panel(
                    "Enter the path to the legal case PDF file you want to analyze:",
                    border_style=self.colors['secondary'],
                    box=box.ROUNDED
                )
            )
            self.console.print()
            
            pdf_path = Prompt.ask(
                f"📄 [bold {self.colors['primary']}]PDF Path[/bold {self.colors['primary']}]",
                default=""
            ).strip('"').strip("'")
            
            if os.path.exists(pdf_path):
                self.console.print(f"[{self.colors['success']}]✓ Valid PDF file found![/{self.colors['success']}]")
                self.console.print()
                return pdf_path
            else:
                self.console.print(f"[{self.colors['error']}]✗ File not found. Please try again.[/{self.colors['error']}]")
                self.console.print()
    
    def show_processing_animation(self, message: str, submessage: str = "", duration: float = 2.0):
        """Show animated processing message with sub-message."""
        display_text = message
        if submessage:
            display_text += f" - {submessage}"
        
        with Progress(
            SpinnerColumn(spinner_name="dots"),
            TextColumn("[bold]{task.description}"),
            console=self.console,
            transient=True
        ) as progress:
            task = progress.add_task(f"[{self.colors['primary']}]{display_text}[/{self.colors['primary']}]", total=None)
            time.sleep(duration)
    
    def get_similarity_color(self, score: float) -> str:
        """Get color for similarity score with bright yet formal gradient effect."""
        if score >= 0.9:
            return self.colors['success']   # Bright emerald green for excellent matches
        elif score >= 0.8:
            return self.colors['accent']    # Bright teal for very good matches
        elif score >= 0.7:
            return self.colors['info']      # Bright sky blue for good matches
        elif score >= 0.6:
            return self.colors['gold']      # Bright gold for moderate matches
        elif score >= 0.5:
            return self.colors['warning']   # Bright amber for fair matches
        else:
            return self.colors['error']     # Bright red for poor matches
    
    def get_similarity_bar(self, score: float, width: int = 20) -> str:
        """Create visual bar for similarity score."""
        filled = int(score * width)
        empty = width - filled
        return '█' * filled + '░' * empty
    
    def display_cosine_similarity_results(self, top_k_cases: List[Tuple[str, float]], 
                                         input_case_info: Dict[str, Any]):
        """Display initial cosine similarity results in a professional table with scores overlaid on bars."""
        self.console.print()
        self.console.print(
            Panel(
                f"[bold {self.colors['primary']}]INITIAL SIMILARITY ANALYSIS[/bold {self.colors['primary']}]",
                border_style=self.colors['primary'],
                box=box.DOUBLE
            )
        )
        self.console.print()
        self.console.print()
        
        # Display input case information
        info_table = Table(
            show_header=False,
            box=box.SIMPLE,
            border_style=self.colors['muted'],
            padding=(0, 1)
        )
        info_table.add_column("Field", style=f"bold {self.colors['secondary']}")
        info_table.add_column("Value", style=self.colors['text'])
        
        if input_case_info:
            metadata = input_case_info.get('metadata', {})
            info_table.add_row("📋 Case Title", metadata.get('case_title', 'Unknown'))
            info_table.add_row("🏛️ Court", metadata.get('court_name', 'Unknown'))
            info_table.add_row("📅 Date", metadata.get('judgment_date', 'Unknown'))
            info_table.add_row("📝 Template", input_case_info.get('template_label', 'Unknown'))
            info_table.add_row("🎯 Template ID", input_case_info.get('template_used', 'Unknown'))
            info_table.add_row("📊 Confidence", f"{input_case_info.get('confidence_score', 0):.3f}")
            
            # Display legal sections
            sections = metadata.get('sections_invoked', [])
            if sections:
                if isinstance(sections, str):
                    info_table.add_row("⚖️  Legal Sections", sections)
                elif isinstance(sections, list):
                    info_table.add_row("⚖️  Legal Sections", ", ".join(sections[:3]) + ("..." if len(sections) > 3 else ""))
            
            # Display primary section
            most_appropriate = metadata.get('most_appropriate_section', 'Unknown')
            if most_appropriate and most_appropriate != 'Unknown':
                info_table.add_row("📌 Primary Section", most_appropriate)
        
        self.console.print(Panel(info_table, title="[bold]Input Case Details[/bold]", border_style=self.colors['secondary']))
        self.console.print()
        
        # Display input case summary
        if input_case_info:
            extracted_facts = input_case_info.get('extracted_facts', {})
            if extracted_facts:
                case_summary = self._extract_facts_as_text_pipeline_style(extracted_facts)
                if case_summary:
                    # Create summary panel
                    summary_panel = Panel(
                        case_summary,
                        title=f"[bold]Input Case Facts Summary ({len(case_summary)} characters)[/bold]",
                        border_style=self.colors['info'],
                        box=box.ROUNDED
                    )
                    self.console.print(summary_panel)
                    self.console.print()
                else:
                    self.console.print(
                        Panel(
                            "No facts summary could be extracted from the input case",
                            title="[bold]Input Case Facts Summary[/bold]",
                            border_style=self.colors['warning'],
                            box=box.ROUNDED
                        )
                    )
                    self.console.print()
            else:
                self.console.print(
                    Panel(
                        "No extracted facts available from the input case",
                        title="[bold]Input Case Facts Summary[/bold]",
                        border_style=self.colors['warning'],
                        box=box.ROUNDED
                    )
                )
                self.console.print()
        
        # Display similarity results with separate columns for score and visual
        table = Table(
            title=f"[bold]Top {len(top_k_cases)} Similar Cases[/bold]",
            box=box.ROUNDED,
            border_style=self.colors['primary'],
            header_style=f"bold {self.colors['primary']}",
            show_lines=True
        )
        
        table.add_column("Rank", justify="center", style="bold", width=6)
        table.add_column("Case Name", style=self.colors['text'], width=32)
        table.add_column("Similarity", justify="center", width=12)
        table.add_column("Visual", justify="left", width=15)
        
        for rank, (case_id, score) in enumerate(top_k_cases, 1):
            # Clean case name
            case_name = case_id.replace('_facts', '').replace('_', ' ')
            if len(case_name) > 30:
                case_name = case_name[:27] + "..."
            
            # Get color and bar
            color = self.get_similarity_color(score)
            bar = self.get_similarity_bar(score, width=10)
            
            table.add_row(
                f"{rank}",
                case_name,
                f"[{color}]{score:.4f}[/{color}]",
                f"[{color}]{bar}[/{color}]"
            )
        
        self.console.print(table)
        self.console.print()
    
    def _extract_facts_as_text(self, facts: Any, parent_key: str = '') -> str:
        """
        Recursively extract facts from nested dictionary structure and return as concatenated text.
        Matches the extraction logic used in the cross-encoder pipeline.
        """
        text_parts = []
        
        if isinstance(facts, dict):
            for key, value in facts.items():
                if value:  # Only process non-empty values
                    current_key = f"{parent_key}.{key}" if parent_key else key
                    
                    if isinstance(value, (dict, list)):
                        # Recursively extract from nested structures
                        nested_text = self._extract_facts_as_text(value, current_key)
                        if nested_text:
                            text_parts.append(nested_text)
                    elif isinstance(value, str):
                        # Add string values directly
                        text_parts.append(value)
                    else:
                        # Convert other types to string
                        text_parts.append(str(value))
        
        elif isinstance(facts, list):
            for item in facts:
                if item:  # Only process non-empty items
                    if isinstance(item, (dict, list)):
                        nested_text = self._extract_facts_as_text(item, parent_key)
                        if nested_text:
                            text_parts.append(nested_text)
                    elif isinstance(item, str):
                        text_parts.append(item)
                    else:
                        text_parts.append(str(item))
        
        return ' '.join(text_parts)
    
    def _load_case_facts(self, case_id: str) -> Dict[str, Any]:
        """
        Load facts for a specific case from the extracted files.
        This matches the _load_case_facts method from the similarity pipeline.
        """
        try:
            from pathlib import Path
            import json
            
            # Try to find the case file in the extracted directory
            cases_dir = Path("cases/extracted")
            
            # Look for files that match the case_id
            possible_files = [
                cases_dir / f"{case_id}_facts.json",
                cases_dir / f"{case_id}.json"
            ]
            
            # Also try direct match
            for file_path in cases_dir.glob("*.json"):
                if case_id in file_path.stem:
                    possible_files.append(file_path)
            
            for file_path in possible_files:
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
            
            return {}
            
        except Exception as e:
            return {}
    
    def _extract_facts_as_text_pipeline_style(self, facts_dict: Dict[str, Any]) -> str:
        """
        Extract fact values from a facts dictionary and concatenate them.
        This matches the _extract_facts_as_text method from the similarity pipeline.
        """
        if not facts_dict:
            return ""
        
        fact_values = []
        
        def extract_values_recursive(obj):
            """Recursively extract string values from nested dictionary/list structures."""
            if isinstance(obj, dict):
                for value in obj.values():
                    extract_values_recursive(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract_values_recursive(item)
            elif isinstance(obj, str) and obj.strip():
                # Only add non-empty strings
                fact_values.append(obj.strip())
        
        extract_values_recursive(facts_dict)
        
        # Join with ". " and ensure proper sentence ending
        result = ". ".join(fact_values)
        if result and not result.endswith('.'):
            result += "."
        
        return result
    
    def _get_case_summary(self, case_id: str, metadata_dict: Dict[str, Any]) -> str:
        """
        Get complete case summary by loading case facts and extracting them as text.
        This matches the approach used in the similarity pipeline's step12_display_results.
        """
        # First try to load case facts directly from files (like pipeline does)
        case_facts = self._load_case_facts(case_id)
        if case_facts:
            case_summary = self._extract_facts_as_text_pipeline_style(case_facts)
            if case_summary:
                return case_summary
        
        # Fallback to metadata if available
        if case_id not in metadata_dict:
            return "No summary available for this case"
        
        case_data = metadata_dict[case_id]
        
        # Try to get from case_texts (if available in metadata)
        if 'case_texts' in metadata_dict and case_id in metadata_dict['case_texts']:
            try:
                import json
                case_text_data = json.loads(metadata_dict['case_texts'][case_id])
                summary = self._extract_facts_as_text_pipeline_style(case_text_data)
                if summary:
                    return summary
            except:
                pass
        
        # Try different keys in case_data
        for key in ['extracted_facts', 'filled_template', 'template_data']:
            if key in case_data and case_data[key]:
                summary = self._extract_facts_as_text_pipeline_style(case_data[key])
                if summary:
                    return summary
        
        return "No summary available for this case"
    
    def display_final_results(self, filtered_cases: List[Tuple[str, float, float]], 
                             input_case_info: Dict[str, Any], 
                             metadata_dict: Dict[str, Any]):
        """Display final re-ranked results in paragraph style with metadata and full summary."""
        self.console.print()
        self.console.print(
            Panel(
                f"[bold {self.colors['success']}]FINAL ANALYSIS RESULTS[/bold {self.colors['success']}]",
                border_style=self.colors['success'],
                box=box.DOUBLE
            )
        )
        self.console.print()
        
        # Check threshold
        threshold = float(os.getenv('CROSS_ENCODER_THRESHOLD', '0.0'))
        
        if not filtered_cases:
            self.console.print(
                Panel(
                    f"[{self.colors['warning']}]No cases found above the threshold ({threshold})\n\n"
                    f"Consider lowering the threshold or reviewing the input case.[/{self.colors['warning']}]",
                    border_style=self.colors['warning'],
                    title="[bold]No Results[/bold]"
                )
            )
            return
        
        # Display each case in detailed paragraph style
        for rank, (case_id, cosine_sim, cross_encoder_score) in enumerate(filtered_cases, 1):
            self.console.print(f"[bold {self.colors['primary']}]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold {self.colors['primary']}]")
            self.console.print()
            
            # Case header with rank
            rank_header = Text()
            rank_header.append(f" RANK #{rank} ", style=f"bold {self.colors['text']}")
            self.console.print(rank_header)
            self.console.print()
            
            # Case name with emoji
            case_title = Text()
            case_title.append("📋 ", style=self.colors['primary'])
            case_title.append(case_id.replace('_facts', '').replace('_', ' '), style=f"{self.colors['text']}")
            self.console.print(case_title)
            self.console.print()
            
            # Combined similarity scores on one line
            scores_text = Text()
            scores_text.append("Cross-Encoder Score: ")
            scores_text.append(f"{cross_encoder_score:.4f} ", style=f"{self.get_similarity_color(cross_encoder_score)}")
            
            # Cross-encoder visual bar
            ce_bar = self.get_similarity_bar(cross_encoder_score, width=11)
            scores_text.append(ce_bar, style=self.get_similarity_color(cross_encoder_score))
            
            scores_text.append(" , Cosine Similarity: ")
            scores_text.append(f"{cosine_sim:.4f} ", style=f"{self.get_similarity_color(cosine_sim)}")
            
            # Cosine visual bar
            cos_bar = self.get_similarity_bar(cosine_sim, width=7)
            scores_text.append(cos_bar, style=self.get_similarity_color(cosine_sim))
            
            self.console.print(scores_text)
            self.console.print()
            
            # Case Details section - try to get metadata like the pipeline does
            details_text = Text()
            details_text.append("Case Details:\n", style=f"bold {self.colors['text']}")
            
            # Try to get metadata from case_texts (like pipeline's existing_metadata)
            case_metadata = {}
            if 'case_texts' in metadata_dict and case_id in metadata_dict['case_texts']:
                try:
                    import json
                    case_data = json.loads(metadata_dict['case_texts'][case_id])
                    if 'tier_4_procedural' in case_data:
                        case_metadata = case_data['tier_4_procedural']
                except:
                    pass
            
            # Fallback to direct metadata if available
            if not case_metadata and case_id in metadata_dict:
                case_metadata = metadata_dict[case_id].get('metadata', {})
            
            if case_metadata:
                details_text.append("  🏛️  Court: ")
                details_text.append(f"{case_metadata.get('court_name', 'Unknown')}\n", style=self.colors['text'])
                details_text.append("  📅 Date: ")
                details_text.append(f"{case_metadata.get('judgment_date', 'Unknown')}\n", style=self.colors['text'])
                
                details_text.append("  ⚖️  Legal Sections: ")
                sections = case_metadata.get('sections_invoked', [])
                if sections:
                    # Handle both string and list cases
                    if isinstance(sections, str):
                        details_text.append(sections, style=self.colors['text'])
                    elif isinstance(sections, list):
                        details_text.append(", ".join(sections), style=self.colors['text'])
                    else:
                        details_text.append(str(sections), style=self.colors['text'])
                else:
                    details_text.append("None specified", style=self.colors['muted'])
            else:
                details_text.append("  No metadata available\n", style=self.colors['muted'])
            
            self.console.print(details_text)
            self.console.print()
            
            # Case summary in a bordered panel - use pipeline-style summary extraction
            summary = self._get_case_summary(case_id, metadata_dict)
            
            if not summary or summary == "No summary available for this case":
                display_summary = "No summary available for this case"
            else:
                display_summary = summary
            
            # Create summary panel with full case summary
            summary_panel = Panel(
                display_summary,
                title=f"[bold]Complete Case Summary[/bold]",
                border_style=self.colors['info'],
                box=box.ROUNDED
            )
            
            self.console.print(summary_panel)
            self.console.print()
    
    def show_error(self, message: str):
        """Display error message."""
        self.console.print(
            Panel(
                f"[bold {self.colors['error']}]ERROR: {message}[/bold {self.colors['error']}]",
                border_style=self.colors['error'],
                box=box.ROUNDED
            )
        )


def main():
    """Main entry point for the CLI."""
    import argparse
    
    parser = argparse.ArgumentParser(description="CaseMind Similarity Analyzer - Rich CLI")
    parser.add_argument("--pdf", help="Path to PDF file (optional, will prompt if not provided)")
    parser.add_argument("--config", default="config.json", help="Path to config file")
    parser.add_argument("--log-dir", default="logs", help="Directory for log files")
    
    args = parser.parse_args()
    
    # Initialize CLI
    cli = RichSimilarityCLI(log_dir=args.log_dir)
    
    try:
        # Show welcome screen
        cli.show_welcome_screen()
        time.sleep(1.5)
        
        # Get file input
        if args.pdf:
            pdf_path = args.pdf
            if not os.path.exists(pdf_path):
                cli.show_error(f"File not found: {pdf_path}")
                return
        else:
            pdf_path = cli.get_file_input()
        
        # Show processing animations with sub-messages
        cli.show_processing_animation("Initializing CaseMind Pipeline", "Analyzing document structure")
        
        # Initialize pipeline
        pipeline = SimilarityCaseSearchPipeline(args.config)
        
        # Process the case
        cli.show_processing_animation("Loading and Converting PDF Document", "Extracting legal metadata")
        validated_pdf_path = pipeline.step1_load_pdf(pdf_path)
        
        cli.show_processing_animation("Converting PDF to structured text format", "Processing document pages")
        markdown_text = pipeline.step2_convert_to_markdown(validated_pdf_path)
        
        cli.show_processing_animation("Extracting Metadata and Legal Facts", "Processing case facts")
        extraction_result = pipeline.step3_to_6_extract_metadata_and_facts(markdown_text, validated_pdf_path)
        
        cli.show_processing_animation("Generating Vector Embeddings", "Computing embeddings")
        new_embedding = pipeline.step7_form_vector_embedding(extraction_result, None)
        
        cli.show_processing_animation("Loading Case Database", "Searching case database")
        existing_embeddings, existing_case_ids, metadata_dict = pipeline.step8_load_stored_embeddings()
        # print(metadata_dict)
        
        cli.show_processing_animation("Computing Cosine Similarity")
        similarities = pipeline.step9_compute_similarity(new_embedding, existing_embeddings, existing_case_ids)
        
        cli.show_processing_animation("Selecting top candidate cases")
        actual_case_id = getattr(pipeline, '_last_case_id_used', None)
        top_k_cases = pipeline.step10_get_top_k_similar(similarities, existing_case_ids, 
                                                        test_case_id=actual_case_id, 
                                                        input_pdf_path=pdf_path)
        
        # Display cosine similarity results
        cli.display_cosine_similarity_results(top_k_cases, extraction_result)
        
        # Re-rank with cross-encoder
        cli.show_processing_animation("Re-ranking cases with deep semantic analysis")
        input_facts = extraction_result.get('extracted_facts', {})
        filtered_cases = pipeline.step11_cross_encoder_rerank(top_k_cases, input_facts)
        
        print(filtered_cases)
        
        # Display final results
        cli.display_final_results(filtered_cases, extraction_result, metadata_dict)
        
        # Show completion message
        cli.console.print()
        completion_text = Text()
        completion_text.append("✓ Analysis Complete : ", style=f"bold {cli.colors['success']}")
        completion_text.append(f" Found {len(filtered_cases)} highly relevant case(s) for your analysis", style=cli.colors['text'])
        cli.console.print(completion_text)
        
    except KeyboardInterrupt:
        cli.console.print(f"\n[{cli.colors['warning']}]Analysis interrupted by user.[/{cli.colors['warning']}]")
    except Exception as e:
        cli.show_error(str(e))
        raise


if __name__ == "__main__":
    main()
