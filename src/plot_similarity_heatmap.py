"""
Simple script to plot heatmap of similarity matrix from existing embeddings.
"""

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sentence_transformers import SentenceTransformer
import glob

def main():
    # Load pretrained Sentence Transformer model
    print("Loading SentenceTransformer model...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    
    # Load embeddings
    npz_files = glob.glob("Embedding results/*.npz")
    if not npz_files:
        print("No embedding files found!")
        return
    
    latest_npz = sorted(npz_files)[-1]
    print(f"Loading embeddings from: {latest_npz}")
    
    # Load data
    data = np.load(latest_npz)
    embeddings = data['embeddings']
    case_ids = data['case_ids']
    
    print(f"Loaded {len(case_ids)} cases")
    print(f"Embeddings shape: {embeddings.shape}")
    
    # Compute similarity matrix using SentenceTransformer's similarity method
    similarities = model.similarity(embeddings, embeddings)
    print(f"Similarity matrix shape: {similarities.shape}")
    print(f"Similarity range: [{similarities.min():.4f}, {similarities.max():.4f}]")
    
    # Create heatmap
    plt.figure(figsize=(12, 10))
    sns.heatmap(similarities.numpy(),  # Convert tensor to numpy for seaborn
                xticklabels=[name[:20] + "..." if len(name) > 20 else name for name in case_ids],
                yticklabels=[name[:20] + "..." if len(name) > 20 else name for name in case_ids],
                cmap='rocket', 
                center=0.5,
                annot=False,
                cbar_kws={'label': 'Similarity Score'})
    
    plt.title("Case Similarity Matrix Heatmap (SentenceTransformer)")
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()