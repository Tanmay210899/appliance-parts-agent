"""
Embeddings Client - Local SBERT embeddings
Uses sentence-transformers for fast local embedding generation
"""

import os
from typing import List, Union
from sentence_transformers import SentenceTransformer
import numpy as np

class EmbeddingsClient:
    """Local SBERT embeddings client"""
    
    def __init__(self):
        self.model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        
        print(f"Loading embedding model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)
        print(f"✓ Model loaded. Embedding dimension: {self.model.get_sentence_embedding_dimension()}")
    
    def embed(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """
        Generate embeddings for text
        
        Args:
            text: Single string or list of strings
        
        Returns:
            Single embedding vector or list of vectors
        """
        if isinstance(text, str):
            # Single text
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        else:
            # Batch of texts
            embeddings = self.model.encode(text, convert_to_numpy=True)
            return embeddings.tolist()
    
    def embed_batch(self, texts: List[str], batch_size: int = 32, show_progress: bool = False) -> List[List[float]]:
        """
        Generate embeddings for large batch of texts
        
        Args:
            texts: List of texts
            batch_size: Batch size for encoding
            show_progress: Show progress bar
        
        Returns:
            List of embedding vectors
        """
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True
        )
        return embeddings.tolist()
    
    @property
    def dimension(self) -> int:
        """Get embedding dimension"""
        return self.model.get_sentence_embedding_dimension()


# Singleton instance
_embeddings_client = None

def get_embeddings_client() -> EmbeddingsClient:
    """Get or create embeddings client instance"""
    global _embeddings_client
    if _embeddings_client is None:
        _embeddings_client = EmbeddingsClient()
    return _embeddings_client
