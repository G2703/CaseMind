"""
Legal Case Embedder - Pipeline Component
Generates and stores vector embeddings for legal case documents.
"""

import json
import os
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from sentence_transformers import SentenceTransformer
import logging

class CaseEmbedder:
    """
    Generates vector embeddings for legal case documents and stores them for future use.
    """
    
    def __init__(self, model_name: str = "all-mpnet-base-v2", output_dir: str = "Embedding results"):
        """
        Initialize the case embedder.
        
        Args:
            model_name (str): HuggingFace model name for sentence transformers
            output_dir (str): Directory to store embeddings and metadata
        """
        self.logger = logging.getLogger(__name__)
        self.model_name = model_name  
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Load the sentence transformer model
        self.logger.info(f"Loading Sentence Transformer model: {model_name}")
        try:
            self.model = SentenceTransformer(model_name)
            self.logger.info(f"Successfully loaded model: {model_name}")
        except Exception as e:
            self.logger.error(f"Failed to load model {model_name}: {e}")
            raise
        
        # Storage for embeddings and metadata
        self.case_embeddings = {}
        self.case_metadata = {}
        
    def extract_case_text(self, case_data: Dict[str, Any]) -> str:
        """
        Convert entire case JSON to text for embedding.
        
        Args:
            case_data (Dict[str, Any]): Case data dictionary
            
        Returns:
            str: Complete case data as text
        """
        # Simply convert the entire JSON to string
        return json.dumps(case_data, ensure_ascii=False, separators=(',', ':'))
    
    def embed_case(self, case_data: Dict[str, Any], case_id: str) -> Dict[str, Any]:
        """
        Generate embeddings for a single case.
        
        Args:
            case_data (Dict[str, Any]): Case data dictionary
            case_id (str): Unique identifier for the case
            
        Returns:
            Dict[str, Any]: Embedding results with metadata
        """
        try:
            # Extract entire case as text
            case_text = self.extract_case_text(case_data)
            
            # Generate embedding
            self.logger.debug(f"Generating embeddings for case: {case_id}")
            embedding = self.model.encode([case_text])[0]
            
            # Store embeddings
            embedding_result = {
                'case_id': case_id,
                'embedding': embedding,
                'case_text': case_text,
                'embedding_dimension': len(embedding),
                'model_name': self.model_name,
                'timestamp': datetime.now().isoformat()
            }
            
            # Simple metadata
            metadata = {
                'case_id': case_id,
                'text_length': len(case_text),
                'timestamp': datetime.now().isoformat()
            }
            
            # Store in memory
            self.case_embeddings[case_id] = embedding_result
            self.case_metadata[case_id] = metadata
            
            self.logger.info(f"Successfully generated embeddings for case: {case_id}")
            return embedding_result
            
        except Exception as e:
            self.logger.error(f"Failed to generate embeddings for case {case_id}: {e}")
            raise
    
    def embed_case_file(self, case_file_path: str) -> Dict[str, Any]:
        """
        Generate embeddings for a case from a JSON file.
        
        Args:
            case_file_path (str): Path to the case JSON file
            
        Returns:
            Dict[str, Any]: Embedding results with metadata
        """
        try:
            # Load case data
            with open(case_file_path, 'r', encoding='utf-8') as f:
                case_data = json.load(f)
            
            # Extract case ID from filename
            case_id = Path(case_file_path).stem.replace('_facts', '')
            
            return self.embed_case(case_data, case_id)
            
        except Exception as e:
            self.logger.error(f"Failed to process case file {case_file_path}: {e}")
            raise
    
    def save_embeddings(self, output_prefix: str = "case_embeddings") -> Dict[str, str]:
        """
        Save all embeddings and metadata to files.
        
        Args:
            output_prefix (str): Prefix for output files
            
        Returns:
            Dict[str, str]: Paths to saved files
        """
        if not self.case_embeddings:
            raise ValueError("No embeddings to save. Generate embeddings first.")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Prepare data for saving
        case_ids = list(self.case_embeddings.keys())
        embeddings = np.array([self.case_embeddings[cid]['embedding'] for cid in case_ids])
        
        # Save embeddings as .npz file
        embeddings_file = self.output_dir / f"{output_prefix}_{timestamp}.npz"
        
        self.logger.info(f"Saving embeddings to {self.output_dir}")
        
        # Save embeddings
        np.savez_compressed(
            embeddings_file,
            embeddings=embeddings,
            case_ids=np.array(case_ids),
            model_name=self.model_name,
            timestamp=timestamp
        )
        
        # Save metadata
        metadata_file = self.output_dir / f"{output_prefix}_metadata_{timestamp}.json"
        
        serializable_metadata = {
            'embeddings_metadata': self.case_metadata,
            'case_texts': {
                cid: self.case_embeddings[cid]['case_text']
                for cid in case_ids
            },
            'model_info': {
                'model_name': self.model_name,
                'embedding_dimension': len(embeddings[0]),
                'total_cases': len(case_ids),
                'timestamp': timestamp
            }
        }
        
        # Save metadata
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(serializable_metadata, f, indent=2, ensure_ascii=False)
        
        saved_files = {
            'embeddings': str(embeddings_file),
            'metadata': str(metadata_file)
        }
        
        self.logger.info(f"✅ Saved embeddings: {embeddings_file}")
        self.logger.info(f"✅ Saved metadata: {metadata_file}")
        
        return saved_files
    
    def load_embeddings(self, embeddings_file: str, metadata_file: Optional[str] = None) -> None:
        """
        Load previously saved embeddings.
        
        Args:
            embeddings_file (str): Path to embeddings .npz file
            metadata_file (str, optional): Path to metadata JSON file
        """
        try:
            # Load embeddings
            data = np.load(embeddings_file)
            embeddings = data['embeddings']
            case_ids = data['case_ids']
            
            # Reconstruct embeddings dictionary
            for i, case_id in enumerate(case_ids):
                self.case_embeddings[case_id] = {
                    'embedding': embeddings[i],
                    'case_id': case_id
                }
            
            # Load metadata if provided
            if metadata_file and os.path.exists(metadata_file):
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                self.case_metadata = metadata.get('embeddings_metadata', {})
            
            self.logger.info(f"Loaded embeddings for {len(case_ids)} cases")
            
        except Exception as e:
            self.logger.error(f"Failed to load embeddings from {embeddings_file}: {e}")
            raise
    
    def get_embedding_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics of generated embeddings.
        
        Returns:
            Dict[str, Any]: Summary statistics
        """
        if not self.case_embeddings:
            return {"message": "No embeddings generated yet"}
        
        case_ids = list(self.case_embeddings.keys())
        
        # Text length statistics
        text_lengths = [self.case_metadata[cid].get('text_length', 0) for cid in case_ids]
        
        summary = {
            'total_cases': len(case_ids),
            'model_name': self.model_name,
            'embedding_dimension': len(list(self.case_embeddings.values())[0]['embedding']),
            'text_statistics': {
                'avg_length': np.mean(text_lengths) if text_lengths else 0,
                'max_length': max(text_lengths) if text_lengths else 0,
                'min_length': min(text_lengths) if text_lengths else 0
            }
        }
        
        return summary