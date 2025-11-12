"""
IPC 392 Template Case Files Embedding and Similarity Analysis - COMBINED VERSION
Compares Key:Value vs Values-Only approaches with side-by-side analysis
"""

import json
from sentence_transformers import SentenceTransformer
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

class IPC392CombinedEmbedder:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        """Initialize the combined embedder with sentence transformer model."""
        print(f"Loading Sentence Transformer model: {model_name}")
        self.model = SentenceTransformer(model_name)
        
        # Data storage
        self.case_files = []
        self.case_names = []
        
        # Key-Value approach data
        self.case_texts_keyvalue = []
        self.embeddings_keyvalue = None
        self.similarity_matrix_keyvalue = None
        
        # Values-Only approach data
        self.case_texts_values_only = []
        self.embeddings_values_only = None
        self.similarity_matrix_values_only = None
        
    def extract_case_text_keyvalue(self, case_data):
        """Extract meaningful text from case JSON data for embedding (Key:Value pairs)."""
        text_parts = []
        
        # Extract from tier 1 (determinative facts)
        tier1_fields = case_data.get('tier_1_determinative', {}).get('fields', {})
        for key, value in tier1_fields.items():
            if value and str(value).strip().lower() not in ['null', 'none', '']:
                text_parts.append(f"{key}: {value}")
        
        # Extract from tier 2 (material facts)
        tier2_fields = case_data.get('tier_2_material', {}).get('fields', {})
        for key, value in tier2_fields.items():
            if value and str(value).strip().lower() not in ['null', 'none', '']:
                text_parts.append(f"{key}: {value}")
        
        # Extract from tier 3 (contextual facts)
        tier3_fields = case_data.get('tier_3_contextual', {}).get('fields', {})
        for key, value in tier3_fields.items():
            if value and str(value).strip().lower() not in ['null', 'none', '']:
                text_parts.append(f"{key}: {value}")
        
        # Extract key procedural information
        tier4_fields = case_data.get('tier_4_procedural', {}).get('fields', {})
        important_procedural = ['case_type', 'sections_invoked', 'acts_and_sections']
        for key in important_procedural:
            if key in tier4_fields and tier4_fields[key]:
                value = tier4_fields[key]
                if isinstance(value, list):
                    value = ', '.join(map(str, value))
                text_parts.append(f"{key}: {value}")
        
        # Extract residual facts
        residual_facts = case_data.get('residual_details', {}).get('unclassified_facts', {})
        for key, value in residual_facts.items():
            if value and str(value).strip().lower() not in ['null', 'none', '']:
                text_parts.append(f"{key}: {value}")
        
        # Combine all text parts
        combined_text = '. '.join(text_parts) if text_parts else "No extractable content"
        return combined_text
    
    def extract_case_values_only(self, case_data):
        """Extract only the values from case JSON data for embedding (NO KEYS)."""
        values = []
        
        # Extract VALUES ONLY from tier 1 (determinative facts)
        tier1_fields = case_data.get('tier_1_determinative', {}).get('fields', {})
        for key, value in tier1_fields.items():
            if value and str(value).strip().lower() not in ['null', 'none', '']:
                values.append(str(value).strip())
        
        # Extract VALUES ONLY from tier 2 (material facts)
        tier2_fields = case_data.get('tier_2_material', {}).get('fields', {})
        for key, value in tier2_fields.items():
            if value and str(value).strip().lower() not in ['null', 'none', '']:
                values.append(str(value).strip())
        
        # Extract VALUES ONLY from tier 3 (contextual facts)
        tier3_fields = case_data.get('tier_3_contextual', {}).get('fields', {})
        for key, value in tier3_fields.items():
            if value and str(value).strip().lower() not in ['null', 'none', '']:
                values.append(str(value).strip())
        
        # Extract VALUES ONLY from key procedural information
        tier4_fields = case_data.get('tier_4_procedural', {}).get('fields', {})
        important_procedural = ['case_type', 'sections_invoked', 'acts_and_sections']
        for key in important_procedural:
            if key in tier4_fields and tier4_fields[key]:
                value = tier4_fields[key]
                if isinstance(value, list):
                    value = ', '.join(map(str, value))
                values.append(str(value).strip())
        
        # Extract VALUES ONLY from residual facts
        residual_facts = case_data.get('residual_details', {}).get('unclassified_facts', {})
        for key, value in residual_facts.items():
            if value and str(value).strip().lower() not in ['null', 'none', '']:
                values.append(str(value).strip())
        
        # Combine all VALUES (no keys)
        combined_text = '. '.join(values) if values else "No extractable values"
        return combined_text, values
    
    def load_case_files(self, folder_path):
        """Load all JSON case files and process them for both approaches."""
        folder = Path(folder_path)
        
        if not folder.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")
        
        # Find all JSON files
        json_files = list(folder.glob("*.json"))
        
        if not json_files:
            raise FileNotFoundError(f"No JSON files found in: {folder_path}")
        
        for json_file in json_files:
            try:
                # Load JSON data
                with open(json_file, 'r', encoding='utf-8') as f:
                    case_data = json.load(f)
                
                # Extract case name (remove _facts.json suffix)
                case_name = json_file.stem.replace('_facts', '')
                
                # Extract text for both approaches
                keyvalue_text = self.extract_case_text_keyvalue(case_data)
                values_only_text, extracted_values = self.extract_case_values_only(case_data)
                
                # Store data
                self.case_files.append(json_file)
                self.case_names.append(case_name)
                self.case_texts_keyvalue.append(keyvalue_text)
                self.case_texts_values_only.append(values_only_text)
                
            except Exception as e:
                print(f"Error loading {json_file}: {e}")
        
        print(f"Loaded {len(self.case_names)} IPC 392 cases for both approaches")
        return len(self.case_names)
    
    def generate_embeddings(self):
        """Generate embeddings for both approaches."""
        if not self.case_texts_keyvalue or not self.case_texts_values_only:
            raise ValueError("No case texts loaded. Call load_case_files() first.")
        
        print(f"Generating embeddings for both approaches...")
        
        # Generate Key:Value embeddings
        print("  - Key:Value embeddings...")
        self.embeddings_keyvalue = self.model.encode(self.case_texts_keyvalue)
        
        # Generate Values-Only embeddings
        print("  - Values-Only embeddings...")
        self.embeddings_values_only = self.model.encode(self.case_texts_values_only)
        
        return self.embeddings_keyvalue, self.embeddings_values_only
    
    def calculate_similarity_matrices(self):
        """Calculate similarity matrices for both approaches."""
        if self.embeddings_keyvalue is None or self.embeddings_values_only is None:
            raise ValueError("No embeddings found. Call generate_embeddings() first.")
        
        print("Calculating similarity matrices for both approaches...")
        
        # Calculate Key:Value similarities
        print("  - Key:Value similarity matrix...")
        self.similarity_matrix_keyvalue = self.model.similarity(self.embeddings_keyvalue, self.embeddings_keyvalue)
        
        # Calculate Values-Only similarities
        print("  - Values-Only similarity matrix...")
        self.similarity_matrix_values_only = self.model.similarity(self.embeddings_values_only, self.embeddings_values_only)
        
        return self.similarity_matrix_keyvalue, self.similarity_matrix_values_only
    
    def display_combined_similarity_matrices(self):
        """Display both similarity matrices side by side."""
        print(f"\n{'='*80}")
        print("SIMILARITY MATRICES COMPARISON")
        print(f"{'='*80}")
        
        # Convert tensors to numpy arrays
        if hasattr(self.similarity_matrix_keyvalue, 'numpy'):
            sim_matrix_kv = self.similarity_matrix_keyvalue.numpy()
        elif hasattr(self.similarity_matrix_keyvalue, 'detach'):
            sim_matrix_kv = self.similarity_matrix_keyvalue.detach().numpy()
        else:
            sim_matrix_kv = np.array(self.similarity_matrix_keyvalue)
            
        if hasattr(self.similarity_matrix_values_only, 'numpy'):
            sim_matrix_vo = self.similarity_matrix_values_only.numpy()
        elif hasattr(self.similarity_matrix_values_only, 'detach'):
            sim_matrix_vo = self.similarity_matrix_values_only.detach().numpy()
        else:
            sim_matrix_vo = np.array(self.similarity_matrix_values_only)
        
        # # Display case names
        # print("Cases:")
        # for i, name in enumerate(self.case_names):
        #     print(f"  Case {i+1}: {name}")
        # print()
        
        # Display Key:Value similarity matrix
        # print("KEY:VALUE SIMILARITY MATRIX:")
        # for i, row in enumerate(sim_matrix_kv):
        #     row_str = " ".join([f"{val:.4f}" for val in row])
        #     print(f"Case {i+1}: [{row_str}]")
        
        # print()
        
        # Display Values-Only similarity matrix
        # print("VALUES-ONLY SIMILARITY MATRIX:")
        # for i, row in enumerate(sim_matrix_vo):
        #     row_str = " ".join([f"{val:.4f}" for val in row])
        #     print(f"Case {i+1}: [{row_str}]")
        
        # print()
        
        # Calculate and display differences
        # print("DIFFERENCE MATRIX (Key:Value - Values-Only):")
        # diff_matrix = sim_matrix_kv - sim_matrix_vo
        # for i, row in enumerate(diff_matrix):
        #     row_str = " ".join([f"{val:+.4f}" for val in row])
        #     print(f"Case {i+1}: [{row_str}]")
    
    def display_combined_heatmaps(self):
        """Generate and display both heatmaps side by side."""
        if self.similarity_matrix_keyvalue is None or self.similarity_matrix_values_only is None:
            raise ValueError("No similarity matrices found. Call calculate_similarity_matrices() first.")
        
        # Convert tensors to numpy arrays
        if hasattr(self.similarity_matrix_keyvalue, 'numpy'):
            sim_matrix_kv = self.similarity_matrix_keyvalue.numpy()
        elif hasattr(self.similarity_matrix_keyvalue, 'detach'):
            sim_matrix_kv = self.similarity_matrix_keyvalue.detach().numpy()
        else:
            sim_matrix_kv = np.array(self.similarity_matrix_keyvalue)
            
        if hasattr(self.similarity_matrix_values_only, 'numpy'):
            sim_matrix_vo = self.similarity_matrix_values_only.numpy()
        elif hasattr(self.similarity_matrix_values_only, 'detach'):
            sim_matrix_vo = self.similarity_matrix_values_only.detach().numpy()
        else:
            sim_matrix_vo = np.array(self.similarity_matrix_values_only)
        
        # Create case numbers for labels (no case names)
        case_numbers = [f"Case {i+1}" for i in range(len(self.case_names))]
        
        # Create figure with subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 8))
        
        # Key:Value heatmap
        sns.heatmap(
            sim_matrix_kv,
            annot=False,
            fmt='.3f',
            cmap='YlOrRd',
            # xticklabels=case_numbers,
            # yticklabels=case_numbers,
            square=True,
            # linewidths=0.5,
            # cbar_kws={'label': 'Cosine Similarity'},
            ax=ax1
        )
        ax1.set_title('Key:Value Approach', fontsize=14, fontweight='bold', pad=20)
        # ax1.set_xlabel('Cases', fontsize=12)
        # ax1.set_ylabel('Cases', fontsize=12)
        # ax1.tick_params(axis='x', rotation=45)
        
        # Values-Only heatmap
        sns.heatmap(
            sim_matrix_vo,
            annot=False,
            fmt='.3f',
            cmap='YlOrRd',
            # xticklabels=case_numbers,
            # yticklabels=case_numbers,
            square=True,
            # linewidths=0.5,
            # cbar_kws={'label': 'Cosine Similarity'},
            ax=ax2
        )
        ax2.set_title('Values-Only Approach', fontsize=14, fontweight='bold', pad=20)
        # ax2.set_xlabel('Cases', fontsize=12)
        # ax2.set_ylabel('Cases', fontsize=12)
        # ax2.tick_params(axis='x', rotation=45)
        
        # Main title
        fig.suptitle('IPC 392 Cases - Similarity Comparison: Key:Value vs Values-Only', 
                    fontsize=16, fontweight='bold', y=0.98)
        
        # Adjust layout
        plt.tight_layout()
        
        # Save the combined plot
        plt.savefig('ipc_392_combined_similarity_heatmaps.png', dpi=300, bbox_inches='tight')
        print("Combined heatmaps saved as 'ipc_392_combined_similarity_heatmaps.png'")
        
        # Show the plot
        try:
            plt.show()
        except KeyboardInterrupt:
            print("Display interrupted - heatmaps saved to file")
        
        plt.close()
        
        # Also create a difference heatmap
        self.display_difference_heatmap(sim_matrix_kv, sim_matrix_vo, case_numbers)
    
    def display_difference_heatmap(self, sim_matrix_kv, sim_matrix_vo, case_labels):
        """Display a heatmap showing the differences between the two approaches."""
        diff_matrix = sim_matrix_kv - sim_matrix_vo
        
        plt.figure(figsize=(10, 8))
        
        # Create difference heatmap
        sns.heatmap(
            diff_matrix,
            annot=False,
            fmt='+.3f',
            cmap='RdBu_r',  # Red-Blue colormap for differences
            center=0,  # Center colormap at 0
            # xticklabels=case_labels,
            # yticklabels=case_labels,
            square=True,
            # linewidths=0.5,
            cbar_kws={'label': 'Similarity Difference (Key:Value - Values-Only)'}
        )
        
        plt.title('Similarity Difference Matrix\n(Key:Value - Values-Only)', 
                 fontsize=14, fontweight='bold', pad=20)
        plt.xlabel('Cases', fontsize=12)
        plt.ylabel('Cases', fontsize=12)
        plt.xticks(rotation=45, ha='right')
        plt.yticks(rotation=0)
        
        plt.tight_layout()
        
        # Save the difference plot
        plt.savefig('ipc_392_similarity_difference_heatmap.png', dpi=300, bbox_inches='tight')
        print("Difference heatmap saved as 'ipc_392_similarity_difference_heatmap.png'")
        
        try:
            plt.show()
        except KeyboardInterrupt:
            print("Display interrupted - difference heatmap saved to file")
        
        plt.close()


def main():
    """Main function to demonstrate the combined IPC 392 case embedding analysis."""
    try:
        # Initialize the combined embedder
        embedder = IPC392CombinedEmbedder()
        
        # Load case files from ipc_397 folder
        folder_path = "cases/extracted"
        embedder.load_case_files(folder_path)
        
        # Generate embeddings for both approaches
        embeddings_kv, embeddings_vo = embedder.generate_embeddings()
        
        # Calculate similarity matrices for both approaches
        similarity_kv, similarity_vo = embedder.calculate_similarity_matrices()
        
        # Display similarity matrices comparison
        embedder.display_combined_similarity_matrices()
        
        # Generate and display combined heatmaps
        print(f"\nGenerating combined similarity heatmaps...")
        embedder.display_combined_heatmaps()
        
        print(f"\n{'='*80}")
        print("IPC 392 COMBINED SIMILARITY ANALYSIS COMPLETE")
        print(f"{'='*80}")
        print(f"✅ Loaded {len(embedder.case_names)} IPC 392 cases")
        print(f"✅ Generated Key:Value embeddings ({embeddings_kv.shape[1]}-dimensional)")
        print(f"✅ Generated Values-Only embeddings ({embeddings_vo.shape[1]}-dimensional)")
        print(f"✅ Calculated both similarity matrices ({similarity_kv.shape[0]}x{similarity_kv.shape[1]})")
        print(f"✅ Generated side-by-side heatmap comparison")
        print(f"✅ Generated difference heatmap visualization")
        print(f"✅ Displayed detailed matrix comparisons")
        
        # Summary of differences
        kv_matrix = similarity_kv.numpy() if hasattr(similarity_kv, 'numpy') else np.array(similarity_kv)
        vo_matrix = similarity_vo.numpy() if hasattr(similarity_vo, 'numpy') else np.array(similarity_vo)
        diff_matrix = kv_matrix - vo_matrix
        
        print(f"\n{'='*60}")
        print("SIMILARITY COMPARISON SUMMARY")
        print(f"{'='*60}")
        print(f"Average Key:Value similarity: {np.mean(kv_matrix[np.triu_indices_from(kv_matrix, k=1)]):.4f}")
        print(f"Average Values-Only similarity: {np.mean(vo_matrix[np.triu_indices_from(vo_matrix, k=1)]):.4f}")
        print(f"Average difference: {np.mean(diff_matrix[np.triu_indices_from(diff_matrix, k=1)]):.4f}")
        print(f"Max positive difference: {np.max(diff_matrix[np.triu_indices_from(diff_matrix, k=1)]):.4f}")
        print(f"Max negative difference: {np.min(diff_matrix[np.triu_indices_from(diff_matrix, k=1)]):.4f}")
        
    except Exception as e:
        print(f"Error during execution: {e}")
        raise


if __name__ == "__main__":
    main()