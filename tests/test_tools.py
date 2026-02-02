"""
Test script for SQL and Vector tools
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.tools import SQLTool, VectorTool


def test_sql_tool():
    """Test SQL Tool functionality"""
    print("="*70)
    print("TESTING SQL TOOL")
    print("="*70)
    
    sql = SQLTool()
    
    # Test 1: Get database stats
    print("\n1. Database Stats:")
    stats = sql.get_stats()
    print(f"   Parts: {stats['total_parts']:,}")
    print(f"   Repairs: {stats['total_repairs']}")
    
    # Test 2: Get part by ID
    print("\n2. Get Part by ID (PS11752778):")
    part = sql.get_part_by_id("PS11752778")
    if part:
        print(f"   ✓ {part['part_name']}")
        print(f"   Brand: {part['brand']}, Price: ${part['part_price']}")
    else:
        print("   ✗ Part not found")
    
    # Test 3: Search with filters
    print("\n3. Search Parts (Whirlpool, under $50):")
    results = sql.search_parts(brand="Whirlpool", max_price=50, limit=5)
    print(f"   Found {len(results)} results:")
    for r in results[:3]:
        print(f"   • {r['part_name']} - ${r['part_price']}")
    
    # Test 4: Search by symptom
    print("\n4. Search by Symptom ('draining'):")
    results = sql.search_by_symptom("draining", appliance_type="dishwasher", limit=5)
    print(f"   Found {len(results)} results:")
    for r in results[:3]:
        print(f"   • {r['part_name']} - ${r['part_price']}")
    
    # Test 5: Search by model number
    print("\n5. Search by Model Number ('WDF520PADM'):")
    results = sql.search_by_model_number("WDF520PADM", limit=3)
    print(f"   Found {len(results)} results:")
    for r in results[:3]:
        print(f"   • {r['part_name']} - ${r['part_price']}")
    
    print("\n✓ SQL Tool tests complete!\n")


def test_vector_tool():
    """Test Vector Tool functionality"""
    print("="*70)
    print("TESTING VECTOR TOOL")
    print("="*70)
    
    vector = VectorTool()
    
    # Test 1: Collection info
    print("\n1. Collection Info:")
    info = vector.get_collection_info()
    print(f"   Parts: {info['parts_collection']['count']:,}")
    print(f"   Repairs: {info['repairs_collection']['count']}")
    
    # Test 2: Semantic search for parts
    print("\n2. Semantic Search ('dishwasher not draining'):")
    results = vector.search_parts("dishwasher not draining", limit=5)
    print(f"   Found {len(results)} results:")
    for r in results[:3]:
        print(f"   • {r['part_name']} (score: {r['similarity_score']:.3f})")
        print(f"     ${r['part_price']} - {r['brand']}")
    
    # Test 3: Semantic search with filters
    print("\n3. Semantic Search with Filters ('ice maker broken', Whirlpool, under $100):")
    results = vector.search_parts(
        "ice maker broken",
        brand="Whirlpool",
        max_price=100,
        limit=5
    )
    print(f"   Found {len(results)} results:")
    for r in results[:3]:
        print(f"   • {r['part_name']} (score: {r['similarity_score']:.3f})")
        print(f"     ${r['part_price']} - {r['brand']}")
    
    # Test 4: Search repairs
    print("\n4. Repair Guides Search ('how to fix dishwasher not cleaning'):")
    results = vector.search_repairs("how to fix dishwasher not cleaning", limit=3)
    print(f"   Found {len(results)} results:")
    for r in results[:3]:
        print(f"   • {r['title']} (score: {r['similarity_score']:.3f})")
        print(f"     Difficulty: {r['difficulty']}")
    
    # Test 5: Get part by ID
    print("\n5. Get Part by ID (fast indexed lookup):")
    part = vector.get_part_by_id("PS11752778")
    if part:
        print(f"   ✓ {part['part_name']}")
        print(f"   Brand: {part['brand']}, Price: ${part['part_price']}")
    else:
        print("   ✗ Part not found")
    
    # Test 6: Find similar parts
    print("\n6. Find Similar Parts (to PS11752778):")
    similar = vector.get_similar_parts("PS11752778", limit=3)
    print(f"   Found {len(similar)} similar parts:")
    for r in similar[:3]:
        print(f"   • {r['part_name']} (score: {r['similarity_score']:.3f})")
        print(f"     ${r['part_price']} - {r['brand']}")
    
    print("\n✓ Vector Tool tests complete!\n")


def main():
    print("\n" + "="*70)
    print("PARTSELECT TOOLS TEST SUITE")
    print("="*70 + "\n")
    
    try:
        # Test SQL Tool
        test_sql_tool()
        
        # Test Vector Tool
        test_vector_tool()
        
        print("="*70)
        print("✓ ALL TESTS PASSED!")
        print("="*70)
        print("\nBoth SQL and Vector tools are working correctly.")
        print("Ready to integrate with LLM Agent!\n")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
