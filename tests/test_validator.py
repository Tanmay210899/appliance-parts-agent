"""
Test the Validator Agent
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents import ValidatorAgent, format_validation_report


def test_validation():
    """Test various validation scenarios"""
    
    validator = ValidatorAgent()
    
    print("="*70)
    print("TESTING VALIDATOR AGENT")
    print("="*70)
    
    # Test Case 1: Valid response with all details
    print("\n" + "="*70)
    print("TEST 1: Valid Response (Should PASS)")
    print("="*70)
    
    user_query = "How much is part PS11752778?"
    tool_results = [{
        "function": "get_part_by_id",
        "args": {"part_id": "PS11752778"},
        "result": {
            "part_id": "PS11752778",
            "part_name": "Refrigerator Door Shelf Bin",
            "part_price": 44.95,
            "brand": "Whirlpool",
            "availability": "In Stock",
            "install_difficulty": "Really Easy",
            "install_time": "Less than 15 minutes",
            "product_url": "https://www.partselect.com/PS11752778",
            "install_video_url": "https://www.youtube.com/watch?v=zSCNN6KpDE8"
        }
    }]
    agent_response = """Part PS11752778 is a Refrigerator Door Shelf Bin for Whirlpool refrigerators.
Price: $44.95
Brand: Whirlpool
Availability: In Stock
Installation: Really Easy (Less than 15 minutes)
Product Page: https://www.partselect.com/PS11752778
Installation Video: https://www.youtube.com/watch?v=zSCNN6KpDE8"""
    
    result = validator.validate(user_query, tool_results, agent_response)
    print(format_validation_report(result))
    
    # Test Case 2: Missing URL (should flag as minor)
    print("\n" + "="*70)
    print("TEST 2: Missing Product URL (Should FLAG)")
    print("="*70)
    
    agent_response_no_url = """Part PS11752778 is a Refrigerator Door Shelf Bin for Whirlpool refrigerators.
Price: $44.95
Brand: Whirlpool
Availability: In Stock"""
    
    result = validator.validate(user_query, tool_results, agent_response_no_url)
    print(format_validation_report(result))
    
    # Test Case 3: Hallucinated price (should reject)
    print("\n" + "="*70)
    print("TEST 3: Hallucinated Price (Should REJECT)")
    print("="*70)
    
    agent_response_wrong_price = """Part PS11752778 is a Refrigerator Door Shelf Bin for Whirlpool refrigerators.
Price: $29.99
Brand: Whirlpool
Availability: In Stock
Product Page: https://www.partselect.com/PS11752778"""
    
    result = validator.validate(user_query, tool_results, agent_response_wrong_price)
    print(format_validation_report(result))
    
    # Test Case 4: Out of scope (should fail scope check)
    print("\n" + "="*70)
    print("TEST 4: Out of Scope Query (Should FAIL)")
    print("="*70)
    
    is_in_scope = validator.validate_scope("What's the weather today?")
    print(f"Scope check result: {'✅ In Scope' if is_in_scope else '❌ Out of Scope'}")
    
    is_in_scope = validator.validate_scope("How do I fix my washing machine?")
    print(f"Washing machine: {'✅ In Scope' if is_in_scope else '❌ Out of Scope'}")
    
    is_in_scope = validator.validate_scope("Dishwasher not draining")
    print(f"Dishwasher query: {'✅ In Scope' if is_in_scope else '❌ Out of Scope'}")
    
    # Test Case 5: Auto-validation with threshold
    print("\n" + "="*70)
    print("TEST 5: Auto-Validation with Thresholds")
    print("="*70)
    
    should_send, reason = validator.auto_validate(
        user_query, 
        tool_results, 
        agent_response_no_url,
        threshold="major"  # Lenient
    )
    print(f"Lenient threshold (major): {'✅ SEND' if should_send else f'❌ REJECT - {reason}'}")
    
    should_send, reason = validator.auto_validate(
        user_query, 
        tool_results, 
        agent_response_no_url,
        threshold="minor"  # Moderate
    )
    print(f"Moderate threshold (minor): {'✅ SEND' if should_send else f'❌ REJECT - {reason}'}")
    
    should_send, reason = validator.auto_validate(
        user_query, 
        tool_results, 
        agent_response_wrong_price,
        threshold="major"
    )
    print(f"Wrong price (lenient): {'✅ SEND' if should_send else f'❌ REJECT - {reason}'}")
    
    print("\n" + "="*70)
    print("✓ VALIDATION TESTING COMPLETE")
    print("="*70)


if __name__ == "__main__":
    test_validation()
