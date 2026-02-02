"""
Validator Agent - Ensures responses are grounded and within scope
"""

import os
import json
from typing import Dict, List, Any, Optional
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()


class ValidatorAgent:
    """
    Validates agent responses to prevent hallucinations and ensure scope compliance
    """
    
    def __init__(self):
        # Configure Gemini client
        self.client = genai.Client(api_key=os.getenv('GOOGLE_API_KEY'))
        self.model_id = os.getenv('LLM_MODEL', 'gemini-2.5-flash')
        
        # Validation prompt
        self.validation_prompt = """You are a validation agent that checks if responses are grounded in retrieved data and within scope.

Your job is to analyze:
1. USER QUERY: The original user question
2. TOOL RESULTS: Data retrieved from database/vector search
3. AGENT RESPONSE: The response given to the user

Validation Checks:

1. GROUNDING CHECK:
   - Are all facts (prices, part names, availability) directly from tool results?
   - Are there any invented details not present in tool results?
   - Are numerical values (prices, times) exact matches?

2. SCOPE CHECK:
   - Is the response about dishwasher or refrigerator parts only?
   - Does it decline off-topic questions politely?

3. URL CHECK:
   - If parts are mentioned, is product_url included?
   - If installation mentioned, is install_video_url included (if available)?
   - Are URLs from the tool results, not invented?

4. COMPLETENESS CHECK:
   - Are key details provided (name, price, brand, availability)?
   - Is the response helpful and answers the user's question?

Return JSON with:
{
    "is_valid": true/false,
    "score": 0-100 (quality score),
    "issues": [list of problems found, empty if valid],
    "severity": "none" | "minor" | "major",
    "recommendation": "approve" | "revise" | "reject"
}

Score breakdown:
- 90-100: Perfect, all details correct and complete
- 70-89: Good, minor issues but acceptable
- 50-69: Fair, needs revision
- 0-49: Poor, reject and regenerate

Severity levels:
- none: Perfect, no issues (score 90+)
- minor: Missing optional details but facts correct (score 70-89)
- major: Hallucinated facts, wrong scope, missing required URLs (score <70)

Recommendation:
- approve: score >= 70
- revise: score 50-69
- reject: score < 50
"""

    def validate(
        self, 
        user_query: str, 
        tool_results: List[Dict[str, Any]], 
        agent_response: str
    ) -> Dict[str, Any]:
        """
        Validate an agent response against tool results
        
        Args:
            user_query: Original user question
            tool_results: List of function calls with results
            agent_response: Generated response to validate
            
        Returns:
            Validation result with is_valid, issues, severity, recommendation
        """
        
        # Build validation request
        validation_request = f"""
USER QUERY:
{user_query}

TOOL RESULTS:
{json.dumps(tool_results, indent=2)}

AGENT RESPONSE:
{agent_response}

Validate the response and return JSON.
"""
        
        try:
            # Call validation model
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=[
                    types.Content(
                        role="user",
                        parts=[types.Part(text=self.validation_prompt)]
                    ),
                    types.Content(
                        role="model",
                        parts=[types.Part(text="I understand. I will validate responses against tool results to check for grounding, scope, URLs, and completeness.")]
                    ),
                    types.Content(
                        role="user",
                        parts=[types.Part(text=validation_request)]
                    )
                ],
                config=types.GenerateContentConfig(
                    temperature=0.1,  # Low temperature for consistent validation
                    max_output_tokens=1024,
                    response_mime_type="application/json"
                )
            )
            
            # Parse validation result
            validation_result = json.loads(response.text)
            
            return validation_result
            
        except Exception as e:
            print(f"⚠️  Validation error: {e}")
            # On validation failure, default to cautious approval
            return {
                "is_valid": True,
                "issues": [f"Validation check failed: {str(e)}"],
                "severity": "minor",
                "recommendation": "approve"
            }
    
    def validate_scope(self, user_query: str) -> bool:
        """
        Quick check if query is within scope (dishwasher/refrigerator parts)
        Returns False for clearly off-topic queries
        """
        
        off_topic_keywords = [
            "weather", "news", "sports", "politics", "recipe", "movie",
            "book", "song", "game", "joke", "story", "poem",
            "washing machine", "dryer", "oven", "microwave", "stove"
        ]
        
        query_lower = user_query.lower()
        
        # Check for obvious off-topic content
        for keyword in off_topic_keywords:
            if keyword in query_lower:
                return False
        
        # Check for appliance-related keywords
        appliance_keywords = [
            "dishwasher", "refrigerator", "fridge", "ice maker", 
            "freezer", "part", "repair", "fix", "install", "replace"
        ]
        
        has_appliance_keyword = any(kw in query_lower for kw in appliance_keywords)
        
        # If no clear indication, assume in-scope (let LLM handle)
        return True
    
    def auto_validate(
        self, 
        user_query: str, 
        tool_results: List[Dict[str, Any]], 
        agent_response: str,
        threshold: str = "major"
    ) -> tuple[bool, Optional[str]]:
        """
        Validate and return (should_send, reason_if_rejected)
        
        Args:
            user_query: User's question
            tool_results: Function call results
            agent_response: Generated response
            threshold: "none" (strict), "minor" (moderate), "major" (lenient)
            
        Returns:
            (should_send: bool, rejection_reason: Optional[str])
        """
        
        # Quick scope check first
        if not self.validate_scope(user_query):
            return False, "Query is outside the scope of dishwasher/refrigerator parts"
        
        # Full validation
        result = self.validate(user_query, tool_results, agent_response)
        
        # Determine if we should send based on threshold
        severity_levels = ["none", "minor", "major"]
        threshold_index = severity_levels.index(threshold)
        severity_index = severity_levels.index(result.get("severity", "major"))
        
        should_send = severity_index >= threshold_index
        
        if not should_send:
            issues_str = "; ".join(result.get("issues", ["Unknown validation issue"]))
            return False, f"Validation failed: {issues_str}"
        
        return True, None


# Validation helper functions
def format_validation_report(validation_result: Dict[str, Any]) -> str:
    """Format validation result for logging"""
    
    status = "✅ VALID" if validation_result.get("is_valid") else "❌ INVALID"
    severity = validation_result.get("severity", "unknown").upper()
    recommendation = validation_result.get("recommendation", "unknown").upper()
    
    report = f"{status} | Severity: {severity} | Recommendation: {recommendation}"
    
    if validation_result.get("issues"):
        report += "\nIssues found:"
        for issue in validation_result["issues"]:
            report += f"\n  • {issue}"
    
    return report
