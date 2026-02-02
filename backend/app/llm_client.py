"""
LLM Client - Model-agnostic wrapper for Google Gemini
Uses the latest google-genai SDK (v1.61.0)
"""

import os
from typing import List, Dict, Optional
from google import genai


class LLMClient:
    """Model-agnostic LLM client using Google Gemini"""
    
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
        
        self.model_name = os.getenv("LLM_MODEL", "gemini-2.0-flash-exp")
        
        # Initialize client with the latest SDK (v1.61.0)
        self.client = genai.Client(api_key=self.api_key)
    
    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        """
        Generate text completion
        
        Args:
            prompt: User prompt
            system_instruction: System instruction/context
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
        
        Returns:
            Generated text
        """
        try:
            # Prepare generation config
            config = {
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }
            
            if system_instruction:
                config["system_instruction"] = system_instruction
            
            # Generate using the latest API
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config,
            )
            
            return response.text
        
        except Exception as e:
            print(f"Error generating response: {e}")
            raise
    
    def generate_with_functions(
        self,
        prompt: str,
        functions: List[Dict],
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
    ) -> Dict:
        """
        Generate with function calling (for Planner Agent)
        
        Args:
            prompt: User prompt
            functions: List of function definitions
            system_instruction: System instruction
            temperature: Sampling temperature
        
        Returns:
            Dict with function calls or text response
        """
        try:
            # Prepare config with tools
            config = {
                "temperature": temperature,
                "tools": [{"function_declarations": functions}],
            }
            
            if system_instruction:
                config["system_instruction"] = system_instruction
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config,
            )
            
            # Parse response for function calls
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and candidate.content.parts:
                    part = candidate.content.parts[0]
                    
                    # Check for function call
                    if hasattr(part, 'function_call') and part.function_call:
                        return {
                            "type": "function_call",
                            "function_name": part.function_call.name,
                            "arguments": dict(part.function_call.args),
                        }
            
            # Default to text response
            return {
                "type": "text",
                "content": response.text,
            }
        
        except Exception as e:
            print(f"Error generating with functions: {e}")
            raise
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
    ) -> str:
        """
        Multi-turn chat completion
        
        Args:
            messages: List of {"role": "user/model", "content": "..."}
            system_instruction: System instruction
            temperature: Sampling temperature
        
        Returns:
            Generated response
        """
        try:
            # Convert messages to contents format
            contents = []
            for msg in messages:
                role = "user" if msg["role"] == "user" else "model"
                contents.append({
                    "role": role,
                    "parts": [{"text": msg["content"]}]
                })
            
            config = {
                "temperature": temperature,
            }
            
            if system_instruction:
                config["system_instruction"] = system_instruction
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config,
            )
            
            return response.text
        
        except Exception as e:
            print(f"Error in chat: {e}")
            raise


# Singleton instance
_llm_client = None

def get_llm_client() -> LLMClient:
    """Get or create LLM client instance"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
