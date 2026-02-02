"""
Planner Agent - Orchestrates SQL and Vector tools using Gemini
"""

import os
import json
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types
from dotenv import load_dotenv

from ..tools import SQLTool, VectorTool
from .validator_agent import ValidatorAgent, format_validation_report

load_dotenv()


class PlannerAgent:
    """
    Intelligent agent that analyzes user queries and orchestrates tool calls
    """
    
    def __init__(self, enable_validation: bool = True):
        # Initialize tools
        self.sql_tool = SQLTool()
        self.vector_tool = VectorTool()
        
        # Initialize validator
        self.enable_validation = enable_validation
        if enable_validation:
            self.validator = ValidatorAgent()
        
        # Configure Gemini client
        self.client = genai.Client(api_key=os.getenv('GOOGLE_API_KEY'))
        
        # Model configuration - use from environment
        self.model_id = os.getenv('LLM_MODEL', 'gemini-2.5-flash')
        self.generation_config = types.GenerateContentConfig(
            temperature=0.1,
            top_p=0.95,
            max_output_tokens=2048,
        )
        
        # System prompt
        self.system_prompt = """You are a PartSelect appliance parts assistant. Your role is to help users find replacement parts for dishwashers and refrigerators, and provide installation guidance.

You have access to:
1. A SQL database with 13,867 parts (structured queries)
2. A vector database with semantic search (symptom-based queries)
3. Repair guides for common problems

When responding about parts:
- Be direct and professional - no conversational fillers like "That's a great question!" or "I'd be happy to help!"
- Use plain text only - NO markdown formatting (no **, no #, no bullets with *)
- Start with a brief explanation or context before listing parts
- ALWAYS include the product page URL (product_url field) so users can purchase the part
- Provide specific details: name, part_id, price, brand, availability
- Include installation difficulty and estimated time when available
- Only include installation video URLs when user explicitly asks about installation, repair guides, or how-to instructions
- When users ask follow-up questions, remember the previous context and parts discussed
- Suggest repair guides for DIY troubleshooting
- Ask clarifying questions if needed (appliance type, model, symptom)
- Keep responses concise and informative

CRITICAL - Context Awareness:
- When user says "it", "this part", "that part", "the part" - refers to the most recently discussed part
- ALWAYS use get_part_by_id FIRST to retrieve the specific part details from conversation history
- Then use those details for related searches
- If user asks about "this part" compatibility but no part was mentioned before, politely ask which part number they're asking about

CRITICAL - Model Number Compatibility:
When users ask "is this part compatible with [model]":
1. If no part was mentioned previously, ask for the part number first
2. If a part WAS mentioned, use get_part_by_id to get part details
3. Use search_by_model_number to check compatibility
4. If search returns 0 results, explain that the specific model isn't in the database, but you can still help them find compatible parts by:
   - Asking what type of part they need (e.g., door bin, water filter, ice maker)
   - Searching by symptom or description
   - OR they can provide more model/appliance info

CRITICAL - Replacement Parts Queries:
When users ask "replacement parts for it", "similar parts", "alternative parts", "what can replace it":
1. FIRST: Use get_part_by_id with the part number from conversation history
2. SECOND: Extract the part's description, appliance_type, and category
3. THIRD: Use search_parts_semantic with a SPECIFIC query based on that part's details
   - Example: If part is "Door Shelf Bin", search for "refrigerator door shelf bin storage"
   - NOT generic queries like "common replacement parts"
4. Return 5-10 similar/alternative parts with full details

CRITICAL - Installation Steps:
When users ask "how to install" or "installation steps" or "how do I install":
1. First use get_part_by_id to get part details
2. Then use search_repair_guides to get installation instructions
3. Provide STEP-BY-STEP instructions from the repair guide FIRST using numbered list
4. Then show the part card at the end

Format for installation responses:
**Installation Steps for [Part Name]:**

1. [Step from repair guide]
2. [Step from repair guide]
3. [Step from repair guide]

---

Part Name (Part #)
Price | Brand | Availability
Product Page: [product_url]
Installation Video: [video_url]

Format for each part (basic):
Part Name (Part #)
Price | Brand | Availability
Product Page: [product_url]

Format when user asks about installation:
Part Name (Part #)
Price | Brand | Availability
Installation: [difficulty] ([time])
Product Page: [product_url]
Installation Video: [install_video_url] (if available)

You ONLY help with dishwasher and refrigerator parts from PartSelect. Politely decline questions outside this scope."""

        # Define function schemas for Gemini
        self.tools = self._create_tool_schemas()
    
    def _create_tool_schemas(self) -> List[Dict]:
        """Create function declarations for Gemini function calling"""
        return [
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name="get_part_by_id",
                        description="Get detailed information about a specific part using its part ID (e.g., PS11752778). Use when user mentions an exact part number.",
                        parameters={
                            "type": "object",
                            "properties": {
                                "part_id": {
                                    "type": "string",
                                    "description": "The part ID (e.g., 'PS11752778')"
                                }
                            },
                            "required": ["part_id"]
                        }
                    ),
                    types.FunctionDeclaration(
                        name="search_parts_semantic",
                        description="Semantic search for parts using natural language descriptions of problems or symptoms (e.g., 'dishwasher not draining', 'leaking ice maker'). Returns parts ranked by relevance. Use for symptom-based queries.",
                        parameters={
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "Natural language query describing the problem or symptom"
                                },
                                "appliance_type": {
                                    "type": "string",
                                    "enum": ["dishwasher", "refrigerator"],
                                    "description": "Filter by appliance type if known"
                                },
                                "brand": {
                                    "type": "string",
                                    "description": "Filter by brand name if specified"
                                },
                                "max_price": {
                                    "type": "number",
                                    "description": "Maximum price filter if user mentions budget"
                                },
                                "limit": {
                                    "type": "integer",
                                    "description": "Max results to return (default 5)",
                                    "default": 5
                                }
                            },
                            "required": ["query"]
                        }
                    ),
                    types.FunctionDeclaration(
                        name="search_parts_filtered",
                        description="Search parts with specific filters like price range, brand, availability, or installation difficulty. Use for structured queries without symptoms.",
                        parameters={
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
                                "limit": {
                                    "type": "integer",
                                    "description": "Max results (default 10)",
                                    "default": 10
                                }
                            }
                        }
                    ),
                    types.FunctionDeclaration(
                        name="search_by_model_number",
                        description="Find parts compatible with a specific appliance model number (e.g., 'WDT780SAEM1'). Use when user provides a model number.",
                        parameters={
                            "type": "object",
                            "properties": {
                                "model_number": {
                                    "type": "string",
                                    "description": "Appliance model number"
                                },
                                "limit": {
                                    "type": "integer",
                                    "description": "Max results (default 10)",
                                    "default": 10
                                }
                            },
                            "required": ["model_number"]
                        }
                    ),
                    types.FunctionDeclaration(
                        name="search_repair_guides",
                        description="Search for DIY repair guides and troubleshooting help. Use when user asks 'how to fix' or wants repair instructions.",
                        parameters={
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "Description of the repair problem"
                                },
                                "product": {
                                    "type": "string",
                                    "enum": ["Dishwasher", "Refrigerator"],
                                    "description": "Appliance type"
                                },
                                "limit": {
                                    "type": "integer",
                                    "description": "Max results (default 3)",
                                    "default": 3
                                }
                            },
                            "required": ["query"]
                        }
                    )
                ]
            )
        ]
    
    def _execute_function(self, function_name: str, args: Dict[str, Any]) -> Any:
        """Execute the appropriate tool function"""
        
        if function_name == "get_part_by_id":
            return self.sql_tool.get_part_by_id(args["part_id"])
        
        elif function_name == "search_parts_semantic":
            return self.vector_tool.search_parts(
                query=args["query"],
                appliance_type=args.get("appliance_type"),
                brand=args.get("brand"),
                max_price=args.get("max_price"),
                limit=args.get("limit", 5)
            )
        
        elif function_name == "search_parts_filtered":
            return self.sql_tool.search_parts(
                appliance_type=args.get("appliance_type"),
                brand=args.get("brand"),
                min_price=args.get("min_price"),
                max_price=args.get("max_price"),
                availability=args.get("availability"),
                limit=args.get("limit", 10)
            )
        
        elif function_name == "search_by_model_number":
            return self.sql_tool.search_by_model_number(
                model_number=args["model_number"],
                limit=args.get("limit", 10)
            )
        
        elif function_name == "search_repair_guides":
            return self.vector_tool.search_repairs(
                query=args["query"],
                product=args.get("product"),
                limit=args.get("limit", 3)
            )
        
        else:
            return {"error": f"Unknown function: {function_name}"}
    
    def chat(
        self, 
        user_message: str, 
        conversation_history: Optional[List[Dict]] = None,
        validation_threshold: int = 60,
        max_retries: int = 2
    ) -> Dict[str, Any]:
        """
        Process user message and return response with validation loop
        
        Args:
            user_message: User's query
            conversation_history: Previous messages for context
            validation_threshold: Minimum score (0-100) to accept response
            max_retries: Maximum regeneration attempts
            
        Returns:
            Dict with response and metadata
        """
        
        # Build conversation contents
        base_contents = []
        
        # Add system instruction as first user message
        base_contents.append(types.Content(
            role="user",
            parts=[types.Part(text=self.system_prompt)]
        ))
        base_contents.append(types.Content(
            role="model",
            parts=[types.Part(text="I understand. I'm a PartSelect assistant helping with dishwasher and refrigerator parts only.")]
        ))
        
        # Add conversation history if provided
        if conversation_history:
            base_contents.extend(conversation_history)
        
        # Add current user message
        base_contents.append(types.Content(
            role="user",
            parts=[types.Part(text=user_message)]
        ))
        
        # Validation loop - retry with feedback if validation fails
        best_response = {
            "response": "I apologize, but I couldn't generate a response. Please try again.",
            "function_calls": [],
            "conversation_history": base_contents,
            "validation": {"score": 0, "issues": []}
        }
        best_score = 0
        validation_attempts = []
        
        for retry_attempt in range(max_retries + 1):
            if retry_attempt > 0:
                print(f"\n🔄 Retry attempt {retry_attempt}/{max_retries}")
            
            # Reset for this attempt
            contents = base_contents.copy()
            function_calls = []
            max_iterations = 3
            iteration = 0
            
            # Function calling loop - simplified for speed
            while iteration < max_iterations:
                # Generate content with tools
                response = self.client.models.generate_content(
                    model=self.model_id,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        temperature=self.generation_config.temperature,
                        top_p=self.generation_config.top_p,
                        max_output_tokens=self.generation_config.max_output_tokens,
                        tools=self.tools
                    )
                )
                
                # Check if we have function calls
                if not response.candidates or not response.candidates[0].content.parts:
                    break
                
                part = response.candidates[0].content.parts[0]
                
                # If no function call, we have final response
                if not hasattr(part, 'function_call') or not part.function_call:
                    break
                
                function_call = part.function_call
                function_name = function_call.name
                function_args = dict(function_call.args)
                
                if retry_attempt == 0:
                    print(f"\n🔧 Function Call: {function_name}")
                    print(f"   Args: {json.dumps(function_args, indent=2)}")
                
                # Execute function
                function_result = self._execute_function(function_name, function_args)
                
                # Track the call
                function_calls.append({
                    "function": function_name,
                    "args": function_args,
                    "result": function_result
                })
                
                if retry_attempt == 0:
                    print(f"   Result: {len(function_result) if isinstance(function_result, list) else 1} items")
                
                # Add model's function call to history
                contents.append(response.candidates[0].content)
                
                # Add function response
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part(
                        function_response=types.FunctionResponse(
                            name=function_name,
                            response={"result": function_result}
                        )
                    )]
                ))
                
                iteration += 1
            
            # Extract final text response
            final_response = None
            if hasattr(response, 'text') and response.text:
                final_response = response.text
            elif hasattr(response, 'candidates') and response.candidates:
                if hasattr(response.candidates[0], 'content') and response.candidates[0].content:
                    if hasattr(response.candidates[0].content, 'parts') and response.candidates[0].content.parts:
                        final_response = response.candidates[0].content.parts[0].text
            
            # If still no response, use fallback
            if not final_response:
                final_response = "I apologize, but I couldn't generate a proper response based on the available information. Please try rephrasing your question."
            
            # Remove duplicate paragraphs/sections that LLM sometimes generates
            final_response = self._deduplicate_response(final_response)
            
            # Validate response if enabled and we have function calls
            validation_result = None
            if self.enable_validation and function_calls:
                print(f"\n🔍 Validating response (Attempt {retry_attempt + 1})...")
                
                validation_result = self.validator.validate(
                    user_query=user_message,
                    tool_results=function_calls,
                    agent_response=final_response
                )
                
                score = validation_result.get("score", 0)
                print(format_validation_report(validation_result))
                print(f"   Score: {score}/100 (threshold: {validation_threshold})")
                
                validation_attempts.append({
                    "attempt": retry_attempt + 1,
                    "score": score,
                    "validation": validation_result
                })
                
                # Track best response
                if score > best_score:
                    best_score = score
                    best_response = {
                        "response": final_response,
                        "function_calls": function_calls,
                        "conversation_history": contents,
                        "validation": validation_result
                    }
                
                # Check if validation passes threshold
                if score >= validation_threshold:
                    print(f"✅ Validation passed! (Score: {score})")
                    return {
                        "response": final_response,
                        "function_calls": function_calls,
                        "conversation_history": contents,
                        "validation": validation_result,
                        "validation_attempts": validation_attempts
                    }
                else:
                    print(f"⚠️  Score {score} below threshold {validation_threshold}")
                    
                    # Add feedback for retry
                    if retry_attempt < max_retries:
                        feedback = f"Previous response had issues (score: {score}/100): {', '.join(validation_result.get('issues', []))}. Please improve the response."
                        base_contents.append(types.Content(
                            role="user",
                            parts=[types.Part(text=feedback)]
                        ))
            else:
                # No validation enabled, return immediately
                return {
                    "response": final_response,
                    "function_calls": function_calls,
                    "conversation_history": contents,
                    "validation": validation_result
                }
        
        # All retries exhausted, return best response
        print(f"\n⚠️  Max retries reached. Returning best response (score: {best_score})")
        
        if best_response and best_response.get("response"):
            best_response["validation_attempts"] = validation_attempts
            return best_response
        
        # Fallback if no valid response generated
        return {
            "response": "I apologize, but I couldn't generate a reliable response after multiple attempts. Please try rephrasing your question or provide more specific details about your appliance.",
            "function_calls": [],
            "conversation_history": base_contents,
            "validation": {"score": 0, "issues": ["Failed to generate valid response after retries"]},
            "validation_attempts": validation_attempts
        }

    def _deduplicate_response(self, text: str) -> str:
        """
        Remove duplicate paragraphs/sections that the LLM sometimes generates.
        Checks for repeated blocks of 2+ sentences and entire response duplication.
        """
        if not text or len(text) < 100:
            return text
        
        # Check if entire response is duplicated (text appears twice)
        # Split by various newline patterns
        text_len = len(text)
        half_len = text_len // 2
        
        # Check if first half matches second half (accounting for extra newlines)
        if text_len > 200 and half_len > 100:
            first_half = text[:half_len].strip()
            second_half = text[half_len:].strip()
            
            # Normalize both halves for comparison
            first_normalized = ' '.join(first_half.lower().split())
            second_normalized = ' '.join(second_half.lower().split())
            
            # If second half starts with first half, it's a duplicate
            if second_normalized.startswith(first_normalized[:200]):
                # Calculate similarity percentage
                min_len = min(len(first_normalized), len(second_normalized))
                if min_len > 0:
                    matching_chars = sum(1 for i in range(min_len) if first_normalized[i] == second_normalized[i])
                    similarity = matching_chars / min_len
                    
                    # If >80% similar, return only first half
                    if similarity > 0.8:
                        return first_half
        
        # Split into paragraphs
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        if len(paragraphs) <= 1:
            return text
        
        # Track seen paragraphs to remove duplicates
        seen = set()
        unique_paragraphs = []
        
        for para in paragraphs:
            # Normalize for comparison (lowercase, remove extra spaces)
            normalized = ' '.join(para.lower().split())
            
            # Only check substantial paragraphs (more than 50 chars)
            if len(normalized) > 50:
                if normalized not in seen:
                    seen.add(normalized)
                    unique_paragraphs.append(para)
            else:
                # Keep short paragraphs (like headers)
                unique_paragraphs.append(para)
        
        return '\n\n'.join(unique_paragraphs)


def format_part_display(part: Dict[str, Any]) -> str:
    """Format a part for display"""
    lines = [
        f"**{part['part_name']}** (Part #{part['part_id']})",
        f"- Brand: {part['brand']}",
        f"- Price: ${part['part_price']}",
        f"- Availability: {part['availability']}"
    ]
    
    if part.get('install_difficulty'):
        lines.append(f"- Installation: {part['install_difficulty']}")
    
    if part.get('install_video_url'):
        lines.append(f"- [Installation Video]({part['install_video_url']})")
    
    if part.get('product_url'):
        lines.append(f"- [Buy Now]({part['product_url']})")
    
    return "\n".join(lines)
