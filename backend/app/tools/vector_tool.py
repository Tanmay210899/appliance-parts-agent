"""
Vector Tool for semantic search against Qdrant
"""

import os
from typing import List, Dict, Optional, Any
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, Range, MatchValue
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()


class VectorTool:
    """Tool for semantic search using Qdrant vector database"""
    
    def __init__(self):
        # Initialize Qdrant client
        self.host = os.getenv("QDRANT_HOST", "localhost")
        self.port = int(os.getenv("QDRANT_PORT", "6333"))
        self.client = QdrantClient(host=self.host, port=self.port)
        
        # Initialize embedding model
        model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        self.model = SentenceTransformer(model_name)
        
        # Collection names
        self.parts_collection = "partselect_parts"
        self.repairs_collection = "partselect_repairs"
    
    def _create_embedding(self, text: str) -> List[float]:
        """Generate embedding for query text"""
        return self.model.encode(text).tolist()
    
    def search_parts(
        self,
        query: str,
        appliance_type: Optional[str] = None,
        brand: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        availability: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Semantic search for parts with optional filters
        
        Args:
            query: Natural language query (e.g., "dishwasher not draining")
            appliance_type: Filter by "dishwasher" or "refrigerator"
            brand: Filter by brand name
            min_price: Minimum price filter
            max_price: Maximum price filter
            availability: Filter by availability status
            limit: Max number of results
            
        Returns:
            List of parts with similarity scores
        """
        # Generate query embedding
        query_vector = self._create_embedding(query)
        
        # Build filters
        must_conditions = []
        
        if appliance_type:
            # Capitalize to match database values: 'Dishwasher', 'Refrigerator'
            must_conditions.append(
                FieldCondition(key="appliance_type", match=MatchValue(value=appliance_type.capitalize()))
            )
        
        if brand:
            must_conditions.append(
                FieldCondition(key="brand", match=MatchValue(value=brand))
            )
        
        if min_price is not None or max_price is not None:
            range_params = {}
            if min_price is not None:
                range_params["gte"] = min_price
            if max_price is not None:
                range_params["lte"] = max_price
            must_conditions.append(
                FieldCondition(key="part_price", range=Range(**range_params))
            )
        
        if availability:
            must_conditions.append(
                FieldCondition(key="availability", match=MatchValue(value=availability))
            )
        
        query_filter = Filter(must=must_conditions) if must_conditions else None
        
        # Perform search
        results = self.client.search(
            collection_name=self.parts_collection,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=limit
        )
        
        # Format results
        formatted_results = []
        for result in results:
            part = result.payload
            part['similarity_score'] = result.score
            formatted_results.append(part)
        
        return formatted_results
    
    def search_repairs(
        self,
        query: str,
        product: Optional[str] = None,
        difficulty: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Semantic search for repair guides
        
        Args:
            query: Natural language query (e.g., "how to fix leaking dishwasher")
            product: Filter by "Dishwasher" or "Refrigerator"
            difficulty: Filter by difficulty level
            limit: Max number of results
            
        Returns:
            List of repair guides with similarity scores
        """
        # Generate query embedding
        query_vector = self._create_embedding(query)
        
        # Build filters
        must_conditions = []
        
        if product:
            must_conditions.append(
                FieldCondition(key="product", match=MatchValue(value=product))
            )
        
        if difficulty:
            must_conditions.append(
                FieldCondition(key="difficulty", match=MatchValue(value=difficulty))
            )
        
        query_filter = Filter(must=must_conditions) if must_conditions else None
        
        # Perform search
        results = self.client.search(
            collection_name=self.repairs_collection,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=limit
        )
        
        # Format results
        formatted_results = []
        for result in results:
            repair = result.payload
            repair['similarity_score'] = result.score
            formatted_results.append(repair)
        
        return formatted_results
    
    def get_part_by_id(self, part_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific part by ID from Qdrant (fast indexed lookup)
        
        Args:
            part_id: Part ID to lookup
            
        Returns:
            Part details or None
        """
        results = self.client.scroll(
            collection_name=self.parts_collection,
            scroll_filter=Filter(
                must=[FieldCondition(key="part_id", match=MatchValue(value=part_id))]
            ),
            limit=1
        )
        
        if results[0]:
            return results[0][0].payload
        return None
    
    def get_parts_by_ids(self, part_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Get multiple parts by IDs from Qdrant
        
        Args:
            part_ids: List of part IDs
            
        Returns:
            List of part details
        """
        if not part_ids:
            return []
        
        results = self.client.scroll(
            collection_name=self.parts_collection,
            scroll_filter=Filter(
                should=[
                    FieldCondition(key="part_id", match=MatchValue(value=pid))
                    for pid in part_ids
                ]
            ),
            limit=len(part_ids)
        )
        
        return [point.payload for point in results[0]]
    
    def get_similar_parts(
        self,
        part_id: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find similar parts to a given part (based on embedding similarity)
        
        Args:
            part_id: Reference part ID
            limit: Max number of similar parts
            
        Returns:
            List of similar parts
        """
        # Get the reference part
        ref_part = self.get_part_by_id(part_id)
        if not ref_part:
            return []
        
        # Use its search_text to find similar parts
        query = ref_part.get('search_text', '')
        if not query:
            return []
        
        # Search for similar parts (exclude the reference part itself)
        results = self.search_parts(query, limit=limit + 1)
        
        # Filter out the reference part
        similar = [r for r in results if r.get('part_id') != part_id]
        return similar[:limit]
    
    def get_collection_info(self) -> Dict[str, Any]:
        """
        Get information about Qdrant collections
        
        Returns:
            Dict with collection stats
        """
        try:
            parts_count = self.client.count(self.parts_collection)
            repairs_count = self.client.count(self.repairs_collection)
            
            return {
                "parts_collection": {
                    "name": self.parts_collection,
                    "count": parts_count.count
                },
                "repairs_collection": {
                    "name": self.repairs_collection,
                    "count": repairs_count.count
                }
            }
        except Exception as e:
            return {"error": str(e)}


# Tool schemas for LLM function calling
VECTOR_TOOL_SCHEMAS = {
    "search_parts": {
        "name": "search_parts_semantic",
        "description": "Semantic search for parts using natural language. Use when user describes a problem or symptom (e.g., 'dishwasher not draining', 'leaking ice maker'). Returns parts ranked by relevance.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language search query describing the problem or part needed"
                },
                "appliance_type": {
                    "type": "string",
                    "enum": ["dishwasher", "refrigerator", "Dishwasher", "Refrigerator"],
                    "description": "Filter by appliance type (case-insensitive)"
                },
                "brand": {
                    "type": "string",
                    "description": "Filter by brand name"
                },
                "min_price": {
                    "type": "number",
                    "description": "Minimum price filter"
                },
                "max_price": {
                    "type": "number",
                    "description": "Maximum price filter"
                },
                "availability": {
                    "type": "string",
                    "description": "Filter by availability (e.g., 'In Stock')"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max number of results (default 10)",
                    "default": 10
                }
            },
            "required": ["query"]
        }
    },
    "search_repairs": {
        "name": "search_repairs",
        "description": "Search for DIY repair guides using natural language. Use when user asks 'how to fix' or wants troubleshooting help.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language query about the repair problem"
                },
                "product": {
                    "type": "string",
                    "enum": ["Dishwasher", "Refrigerator"],
                    "description": "Filter by appliance type"
                },
                "difficulty": {
                    "type": "string",
                    "description": "Filter by difficulty level"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max number of results (default 5)",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    },
    "get_similar_parts": {
        "name": "get_similar_parts",
        "description": "Find parts similar to a given part. Use when user wants alternatives or 'parts like this one'.",
        "parameters": {
            "type": "object",
            "properties": {
                "part_id": {
                    "type": "string",
                    "description": "Reference part ID to find similar parts"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max number of similar parts (default 5)",
                    "default": 5
                }
            },
            "required": ["part_id"]
        }
    }
}
