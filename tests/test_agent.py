"""
Test the Planner Agent with sample queries
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents import PlannerAgent


def test_agent():
    """Test the agent with various queries"""
    
    print("="*70)
    print("TESTING PLANNER AGENT")
    print("="*70)
    
    # Initialize agent
    agent = PlannerAgent()
    
    # Test queries
    test_queries = [
        "How can I install part number PS11752778?",
        "Is this part compatible with my WDT780SAEM1 model?",
        "The ice maker on my Whirlpool fridge is not working. How can I fix it?",
        "Show me cheap Whirlpool dishwasher parts under $50",
        "My dishwasher is not draining properly"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*70}")
        print(f"TEST {i}: {query}")
        print('='*70)
        
        try:
            result = agent.chat(query, validation_threshold=70, max_retries=2)
            
            # Show function calls
            if result['function_calls']:
                print(f"\n📞 Function Calls Made: {len(result['function_calls'])}")
                for fc in result['function_calls']:
                    print(f"   • {fc['function']}({list(fc['args'].keys())})")
                    if isinstance(fc['result'], list):
                        print(f"     → Returned {len(fc['result'])} results")
                    elif fc['result']:
                        print(f"     → Returned 1 result")
                    else:
                        print(f"     → No results")
            
            # Show validation info
            if result.get('validation'):
                validation = result['validation']
                print(f"\n🔍 Validation: Score {validation.get('score', 'N/A')}/100")
                if result.get('validation_attempts') and len(result['validation_attempts']) > 1:
                    print(f"   Attempts: {len(result['validation_attempts'])}")
            
            # Show response
            print(f"\n💬 Agent Response:")
            print("-" * 70)
            print(result['response'])
            print("-" * 70)
            
        except Exception as e:
            print(f"\n✗ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*70}")
    print("✓ AGENT TESTING COMPLETE")
    print('='*70)


def interactive_mode():
    """Interactive chat mode"""
    print("\n" + "="*70)
    print("INTERACTIVE CHAT MODE")
    print("="*70)
    print("Type 'exit' or 'quit' to stop\n")
    
    agent = PlannerAgent()
    conversation_history = []
    
    while True:
        try:
            user_input = input("\n👤 You: ").strip()
            
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("\nGoodbye! 👋")
                break
            
            if not user_input:
                continue
            
            # Get response
            result = agent.chat(user_input, conversation_history)
            
            # Update history
            conversation_history = result['conversation_history']
            
            # Show function calls (optional debug info)
            if result['function_calls']:
                print(f"\n🔧 [Called {len(result['function_calls'])} function(s)]")
            
            # Show response
            print(f"\n🤖 Agent: {result['response']}")
            
        except KeyboardInterrupt:
            print("\n\nGoodbye! 👋")
            break
        except Exception as e:
            print(f"\n✗ Error: {e}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Test the Planner Agent')
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='Run in interactive chat mode')
    
    args = parser.parse_args()
    
    if args.interactive:
        interactive_mode()
    else:
        test_agent()


if __name__ == "__main__":
    main()
