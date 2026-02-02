"""
SQL Tool for structured queries against PostgreSQL
Safe, template-based queries with parameterization
"""

import os
from typing import List, Dict, Optional, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()


class SQLTool:
    """Tool for querying PostgreSQL database with safe, parameterized queries"""
    
    def __init__(self):
        self.connection_params = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': os.getenv('POSTGRES_PORT', '5432'),
            'database': os.getenv('POSTGRES_DB', 'partselect'),
            'user': os.getenv('POSTGRES_USER', 'postgres'),
            'password': os.getenv('POSTGRES_PASSWORD', '')
        }
    
    def _get_connection(self):
        """Create database connection"""
        return psycopg2.connect(**self.connection_params)
    
    def get_part_by_id(self, part_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a single part by its part_id
        
        Args:
            part_id: Part ID (e.g., "PS11752778")
            
        Returns:
            Dict with part details or None if not found
        """
        query = """
            SELECT 
                part_id, part_name, mpn_id, brand, part_price,
                availability, install_difficulty, install_time,
                product_types, symptoms, replace_parts,
                install_video_url, product_url, appliance_type
            FROM parts
            WHERE part_id = %s
        """
        
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, (part_id,))
                result = cursor.fetchone()
                return dict(result) if result else None
    
    def get_parts_by_ids(self, part_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Get multiple parts by their part_ids
        
        Args:
            part_ids: List of part IDs
            
        Returns:
            List of dicts with part details
        """
        if not part_ids:
            return []
        
        query = """
            SELECT 
                part_id, part_name, mpn_id, brand, part_price,
                availability, install_difficulty, install_time,
                product_types, symptoms, replace_parts,
                install_video_url, product_url, appliance_type
            FROM parts
            WHERE part_id = ANY(%s)
            ORDER BY part_price ASC
        """
        
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, (part_ids,))
                results = cursor.fetchall()
                return [dict(row) for row in results]
    
    def search_parts(
        self,
        appliance_type: Optional[str] = None,
        brand: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        availability: Optional[str] = None,
        install_difficulty: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search parts with structured filters
        
        Args:
            appliance_type: "dishwasher" or "refrigerator"
            brand: Brand name (e.g., "Whirlpool")
            min_price: Minimum price
            max_price: Maximum price
            availability: "In Stock", "Backorder", etc.
            install_difficulty: "Easy", "Moderate", "Hard"
            limit: Max results to return
            
        Returns:
            List of matching parts
        """
        conditions = []
        params = []
        
        if appliance_type:
            conditions.append("LOWER(appliance_type) = LOWER(%s)")
            params.append(appliance_type)
        
        if brand:
            conditions.append("LOWER(brand) = LOWER(%s)")
            params.append(brand)
        
        if min_price is not None:
            conditions.append("part_price >= %s")
            params.append(min_price)
        
        if max_price is not None:
            conditions.append("part_price <= %s")
            params.append(max_price)
        
        if availability:
            conditions.append("LOWER(availability) = LOWER(%s)")
            params.append(availability)
        
        if install_difficulty:
            conditions.append("LOWER(install_difficulty) = LOWER(%s)")
            params.append(install_difficulty)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        query = f"""
            SELECT 
                part_id, part_name, mpn_id, brand, part_price,
                availability, install_difficulty, install_time,
                product_types, symptoms, replace_parts,
                install_video_url, product_url, appliance_type
            FROM parts
            WHERE {where_clause}
            ORDER BY part_price ASC
            LIMIT %s
        """
        
        params.append(limit)
        
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                results = cursor.fetchall()
                return [dict(row) for row in results]
    
    def search_by_symptom(
        self,
        symptom: str,
        appliance_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Full-text search on symptoms field
        
        Args:
            symptom: Symptom keyword (e.g., "draining", "leaking")
            appliance_type: Optional appliance filter
            limit: Max results
            
        Returns:
            List of matching parts
        """
        conditions = ["symptoms ILIKE %s"]
        params = [f"%{symptom}%"]
        
        if appliance_type:
            conditions.append("appliance_type = %s")
            params.append(appliance_type.lower())
        
        where_clause = " AND ".join(conditions)
        
        query = f"""
            SELECT 
                part_id, part_name, mpn_id, brand, part_price,
                availability, install_difficulty, install_time,
                product_types, symptoms, replace_parts,
                install_video_url, product_url, appliance_type
            FROM parts
            WHERE {where_clause}
            ORDER BY part_price ASC
            LIMIT %s
        """
        
        params.append(limit)
        
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                results = cursor.fetchall()
                return [dict(row) for row in results]
    
    def search_by_model_number(
        self,
        model_number: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for parts compatible with a specific model number
        
        Args:
            model_number: Model number to search for
            limit: Max results
            
        Returns:
            List of compatible parts
        """
        query = """
            SELECT 
                part_id, part_name, mpn_id, brand, part_price,
                availability, install_difficulty, install_time,
                product_types, symptoms, replace_parts,
                install_video_url, product_url, appliance_type
            FROM parts
            WHERE product_types ILIKE %s
            ORDER BY part_price ASC
            LIMIT %s
        """
        
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, (f"%{model_number}%", limit))
                results = cursor.fetchall()
                return [dict(row) for row in results]
    
    def get_repair_guides(
        self,
        product: Optional[str] = None,
        difficulty: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get repair guides from repairs table
        
        Args:
            product: "Dishwasher" or "Refrigerator"
            difficulty: "REALLY EASY", "EASY", "MODERATE", "HARD"
            
        Returns:
            List of repair guides
        """
        conditions = []
        params = []
        
        if product:
            conditions.append("LOWER(product) = LOWER(%s)")
            params.append(product)
        
        if difficulty:
            conditions.append("LOWER(difficulty) = LOWER(%s)")
            params.append(difficulty)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        query = f"""
            SELECT *
            FROM repairs
            WHERE {where_clause}
            ORDER BY percentage DESC
        """
        
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                results = cursor.fetchall()
                return [dict(row) for row in results]
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get database statistics
        
        Returns:
            Dict with counts
        """
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM parts")
                parts_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM repairs")
                repairs_count = cursor.fetchone()[0]
                
                return {
                    "total_parts": parts_count,
                    "total_repairs": repairs_count
                }


# Tool schema for LLM function calling
SQL_TOOL_SCHEMAS = {
    "get_part_by_id": {
        "name": "get_part_by_id",
        "description": "Get detailed information about a specific part by its part_id. Use when user provides exact part ID like 'PS11752778'.",
        "parameters": {
            "type": "object",
            "properties": {
                "part_id": {
                    "type": "string",
                    "description": "The part ID (e.g., 'PS11752778')"
                }
            },
            "required": ["part_id"]
        }
    },
    "search_parts": {
        "name": "search_parts",
        "description": "Search parts using structured filters like price, brand, availability, install difficulty. Use for queries with specific filtering criteria.",
        "parameters": {
            "type": "object",
            "properties": {
                "appliance_type": {
                    "type": "string",
                    "enum": ["dishwasher", "refrigerator"],
                    "description": "Type of appliance"
                },
                "brand": {
                    "type": "string",
                    "description": "Brand name (e.g., 'Whirlpool', 'GE')"
                },
                "min_price": {
                    "type": "number",
                    "description": "Minimum price in dollars"
                },
                "max_price": {
                    "type": "number",
                    "description": "Maximum price in dollars"
                },
                "availability": {
                    "type": "string",
                    "description": "Availability status (e.g., 'In Stock')"
                },
                "install_difficulty": {
                    "type": "string",
                    "description": "Installation difficulty level"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max number of results (default 10)",
                    "default": 10
                }
            }
        }
    },
    "search_by_model_number": {
        "name": "search_by_model_number",
        "description": "Find parts compatible with a specific appliance model number. Use when user provides model number like 'WDF520PADM'.",
        "parameters": {
            "type": "object",
            "properties": {
                "model_number": {
                    "type": "string",
                    "description": "Appliance model number"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max number of results (default 10)",
                    "default": 10
                }
            },
            "required": ["model_number"]
        }
    }
}
