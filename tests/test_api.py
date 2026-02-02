"""
Test script for FastAPI endpoints
Run this while the API server is running on localhost:8000
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health check endpoint"""
    print("\n" + "="*70)
    print("TEST 1: Health Check")
    print("="*70)
    
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200


def test_create_session():
    """Test session creation"""
    print("\n" + "="*70)
    print("TEST 2: Create Session")
    print("="*70)
    
    response = requests.post(f"{BASE_URL}/api/session/new")
    print(f"Status Code: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")
    return data.get("session_id") if response.status_code == 200 else None


def test_chat(session_id=None):
    """Test chat endpoint"""
    print("\n" + "="*70)
    print("TEST 3: Chat Request")
    print("="*70)
    
    payload = {
        "message": "Show me cheap Whirlpool dishwasher parts under $50",
        "enable_validation": True,
        "validation_threshold": 70
    }
    
    if session_id:
        payload["session_id"] = session_id
        print(f"Using session ID: {session_id}")
    
    print(f"Request: {json.dumps(payload, indent=2)}")
    print("\nSending request...")
    
    response = requests.post(f"{BASE_URL}/api/chat", json=payload)
    print(f"\nStatus Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\nSession ID: {data.get('session_id')}")
        print(f"Validation Score: {data.get('validation_score')}")
        print(f"\nResponse:\n{data.get('response')}")
        return data.get('session_id')
    else:
        print(f"Error: {response.text}")
        return None


def test_session_history(session_id):
    """Test getting session history"""
    print("\n" + "="*70)
    print("TEST 4: Get Session History")
    print("="*70)
    
    response = requests.get(f"{BASE_URL}/api/session/{session_id}/history")
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Session: {data.get('session_id')}")
        print(f"History entries: {len(data.get('history', []))}")
        for i, entry in enumerate(data.get('history', []), 1):
            print(f"\n  Entry {i}:")
            print(f"    User: {entry.get('user')[:50]}...")
            print(f"    Agent: {entry.get('agent')[:100]}...")
    else:
        print(f"Error: {response.text}")


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("PARTSELECT CHATBOT API TESTS")
    print("="*70)
    print(f"Base URL: {BASE_URL}")
    print("Make sure the API server is running!")
    
    try:
        # Test 1: Health check
        if not test_health():
            print("\n❌ Health check failed!")
            return
        
        # Test 2: Create session
        session_id = test_create_session()
        if not session_id:
            print("\n❌ Session creation failed!")
            return
        
        # Test 3: Chat
        returned_session_id = test_chat(session_id)
        if not returned_session_id:
            print("\n❌ Chat request failed!")
            return
        
        # Test 4: Get history
        test_session_history(returned_session_id)
        
        print("\n" + "="*70)
        print("✅ ALL TESTS COMPLETED")
        print("="*70)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to API server")
        print("Make sure the server is running: python -m uvicorn backend.app.main:app --reload")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")


if __name__ == "__main__":
    main()
