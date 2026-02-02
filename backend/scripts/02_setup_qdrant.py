"""
Step 2: Qdrant Vector Database Setup
Generate embeddings and load into Qdrant for semantic search
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import time

# Load environment variables
load_dotenv()

def get_qdrant_client():
    """Initialize Qdrant client"""
    host = os.getenv("QDRANT_HOST", "localhost")
    port = int(os.getenv("QDRANT_PORT", "6333"))
    
    client = QdrantClient(host=host, port=port)
    return client

def load_embedding_model():
    """Load SBERT embedding model"""
    model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    print(f"Loading embedding model: {model_name}")
    model = SentenceTransformer(model_name)
    print(f"✓ Model loaded (dimension: {model.get_sentence_embedding_dimension()})")
    return model

def load_parts_from_csv():
    """Load parts directly from CSV files"""
    print("\nLoading parts from CSV files...")
    
    project_root = Path(__file__).parent.parent.parent
    data_dir = project_root / "data"
    
    # Load all CSV files
    csv_files = list(data_dir.glob("*_parts.csv"))
    
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {data_dir}")
    
    # Read and concatenate all parts
    dfs = []
    for csv_file in csv_files:
        df = pd.read_csv(csv_file)
        
        # Add appliance_type based on filename (same as PostgreSQL setup)
        if 'dishwasher' in csv_file.name.lower():
            df['appliance_type'] = 'Dishwasher'
        elif 'refrigerator' in csv_file.name.lower() or 'fridge' in csv_file.name.lower():
            df['appliance_type'] = 'Refrigerator'
        else:
            df['appliance_type'] = 'Unknown'
        
        dfs.append(df)
        print(f"  Loaded {len(df):,} parts from {csv_file.name}")
    
    all_parts = pd.concat(dfs, ignore_index=True)
    
    # Ensure consistent column names (lowercase)
    all_parts.columns = all_parts.columns.str.lower()
    
    print(f"✓ Total parts loaded: {len(all_parts):,}")
    return all_parts

def load_repairs_from_csv():
    """Load repair guides directly from CSV file"""
    print("\nLoading repair guides from CSV...")
    
    project_root = Path(__file__).parent.parent.parent
    data_dir = project_root / "data"
    repairs_file = data_dir / "repairs.csv"
    
    if not repairs_file.exists():
        print(f"  Warning: No repairs.csv found in {data_dir}")
        return None
    
    repairs_df = pd.read_csv(repairs_file)
    repairs_df.columns = repairs_df.columns.str.lower()
    
    print(f"✓ Loaded {len(repairs_df):,} repair guides")
    return repairs_df

def create_text_for_embedding_parts(row):
    """Create semantic text blob for parts embedding - ONLY natural language fields"""
    
    # EMBED: Natural language fields where semantic similarity helps
    # DON'T EMBED: Structured facts (price, brand, availability, URLs, etc.)
    
    text_parts = [
        str(row.get('part_name', '')),
        str(row.get('appliance_type', ''))
    ]
    
    # Product description - what the part is and does
    product_description = row.get('product_description', '')
    if product_description and str(product_description) not in ["N/A", "nan", "", "None"]:
        text_parts.append(str(product_description))
    
    # Symptoms - KEY for user queries like "not draining", "leaking", "noisy"
    symptoms = row.get('symptoms', '')
    if symptoms and str(symptoms) not in ["N/A", "nan", "", "None"]:
        text_parts.append(f"Fixes: {symptoms}")
    
    # Product types - compatibility info
    product_types = row.get('product_types', '')
    if product_types and str(product_types) not in ["N/A", "nan", "", "None"]:
        text_parts.append(f"Compatible: {product_types}")
    
    # Installation story - CHUNK to first 600 chars (most relevant part)
    installation_story = row.get('installation_story', '')
    if installation_story and str(installation_story) not in ["N/A", "nan", "", "None"]:
        story_chunk = str(installation_story)[:600].strip()
        if story_chunk:
            text_parts.append(f"User experience: {story_chunk}")
    
    # Structured fields (price, brand, availability, install_time, URLs) 
    # are stored in payload ONLY, not embedded
    
    return " | ".join(text_parts)

def create_text_for_embedding_repairs(row):
    """Create semantic text blob for repair guides embedding"""
    
    # Map CSV fields: symptom=title, Product=product, description=repair_guide
    symptom = str(row.get('symptom', ''))
    product = str(row.get('Product', row.get('product', '')))  # Handle both cases
    
    text_parts = [symptom, product]
    
    # Repair guide content - chunk to 800 chars (repair steps are valuable)
    description = row.get('description', '')
    if description and str(description) not in ["N/A", "nan", "", "None"]:
        guide_chunk = str(description)[:800].strip()
        if guide_chunk:
            text_parts.append(guide_chunk)
    
    # Add parts list for better matching
    parts = row.get('parts', '')
    if parts and str(parts) not in ["N/A", "nan", "", "None"]:
        text_parts.append(f"Parts needed: {parts}")
    
    return " | ".join(text_parts)

def setup_qdrant_collection(client, model, collection_name, collection_type="parts"):
    """Create Qdrant collection with proper configuration and indexes"""
    vector_size = model.get_sentence_embedding_dimension()
    
    print(f"\nSetting up Qdrant collection: {collection_name}")
    
    # Delete existing collection if it exists
    try:
        client.delete_collection(collection_name)
        print("  Deleted existing collection")
    except:
        pass
    
    # Create new collection
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=vector_size,
            distance=Distance.COSINE
        )
    )
    
    print(f"✓ Collection created (vector size: {vector_size}, distance: COSINE)")
    
    # Create payload indexes for fast filtering
    print("  Creating payload indexes...")
    
    if collection_type == "parts":
        # Index IDs for fast lookups
        client.create_payload_index(
            collection_name=collection_name,
            field_name="part_id",
            field_schema="keyword"
        )
        client.create_payload_index(
            collection_name=collection_name,
            field_name="mpn_id",
            field_schema="keyword"
        )
        # Index commonly filtered fields
        client.create_payload_index(
            collection_name=collection_name,
            field_name="brand",
            field_schema="keyword"
        )
        client.create_payload_index(
            collection_name=collection_name,
            field_name="appliance_type",
            field_schema="keyword"
        )
        client.create_payload_index(
            collection_name=collection_name,
            field_name="part_price",
            field_schema="float"
        )
        client.create_payload_index(
            collection_name=collection_name,
            field_name="availability",
            field_schema="keyword"
        )
        print("  ✓ Created indexes: part_id, mpn_id, brand, appliance_type, part_price, availability")
    
    elif collection_type == "repairs":
        # Index IDs for fast lookups
        client.create_payload_index(
            collection_name=collection_name,
            field_name="repair_id",
            field_schema="keyword"
        )
        # Index commonly filtered fields for repairs
        client.create_payload_index(
            collection_name=collection_name,
            field_name="product",
            field_schema="keyword"
        )
        client.create_payload_index(
            collection_name=collection_name,
            field_name="difficulty",
            field_schema="keyword"
        )
        print("  ✓ Created indexes: repair_id, product, difficulty")
    
    return collection_name

def generate_and_upload_embeddings_parts(client, model, collection_name, parts_df):
    """Generate embeddings for parts and upload to Qdrant"""
    print(f"\nGenerating embeddings for {len(parts_df):,} parts...")
    print("This may take a few minutes...")
    
    batch_size = 100
    points = []
    
    start_time = time.time()
    
    for i, (idx, row) in enumerate(tqdm(parts_df.iterrows(), total=len(parts_df), desc="Processing parts")):
        
        # Create text for embedding
        text = create_text_for_embedding_parts(row)
        
        # Generate embedding
        embedding = model.encode(text).tolist()
        
        # Create payload with all part data (handle NaN values)
        payload = {
            "part_id": str(row.get('part_id', '')),
            "part_name": str(row.get('part_name', '')),
            "mpn_id": str(row.get('mpn_id', '')),
            "brand": str(row.get('brand', '')),
            "part_price": float(row.get('part_price', 0)) if pd.notna(row.get('part_price')) else 0.0,
            "availability": str(row.get('availability', '')),
            "install_difficulty": str(row.get('install_difficulty', '')),
            "install_time": str(row.get('install_time', '')),
            "product_types": str(row.get('product_types', '')),
            "symptoms": str(row.get('symptoms', '')),
            "replace_parts": str(row.get('replace_parts', '')),
            "product_description": str(row.get('product_description', '')),
            "installation_story": str(row.get('installation_story', '')),
            "install_video_url": str(row.get('install_video_url', '')),
            "product_url": str(row.get('product_url', '')),
            "appliance_type": str(row.get('appliance_type', '')),
            "search_text": text
        }
        
        # Create point
        point = PointStruct(
            id=i,
            vector=embedding,
            payload=payload
        )
        
        points.append(point)
        
        # Upload in batches
        if len(points) >= batch_size:
            client.upsert(
                collection_name=collection_name,
                points=points
            )
            points = []
    
    # Upload remaining points
    if points:
        client.upsert(
            collection_name=collection_name,
            points=points
        )
    
    elapsed = time.time() - start_time
    print(f"\n✓ All part embeddings generated and uploaded in {elapsed:.1f}s")
    print(f"  Average: {elapsed/len(parts_df)*1000:.1f}ms per part")

def generate_and_upload_embeddings_repairs(client, model, collection_name, repairs_df):
    """Generate embeddings for repair guides and upload to Qdrant"""
    print(f"\nGenerating embeddings for {len(repairs_df):,} repair guides...")
    
    points = []
    start_time = time.time()
    
    for i, (idx, row) in enumerate(tqdm(repairs_df.iterrows(), total=len(repairs_df), desc="Processing repairs")):
        
        # Create text for embedding
        text = create_text_for_embedding_repairs(row)
        
        # Generate embedding
        embedding = model.encode(text).tolist()
        
        # Map CSV fields to payload
        product = str(row.get('Product', row.get('product', '')))
        symptom = str(row.get('symptom', ''))
        description = str(row.get('description', ''))
        difficulty = str(row.get('difficulty', ''))
        parts = str(row.get('parts', ''))
        percentage = str(row.get('percentage', ''))
        video_url = str(row.get('repair_video_url', ''))
        url = str(row.get('symptom_detail_url', ''))
        
        # Create payload with repair guide data
        payload = {
            "repair_id": str(i),
            "title": symptom,  # symptom is the title
            "product": product,  # Appliance type
            "problem": symptom,  # Also store as problem
            "difficulty": difficulty,
            "percentage": percentage,  # Popularity percentage
            "parts": parts,  # Parts needed for this repair
            "repair_guide": description,  # Full repair guide
            "video_url": video_url,
            "url": url,
            "search_text": text
        }
        
        # Create point
        point = PointStruct(
            id=i,
            vector=embedding,
            payload=payload
        )
        
        points.append(point)
    
    # Upload all repair points
    if points:
        client.upsert(
            collection_name=collection_name,
            points=points
        )
    
    elapsed = time.time() - start_time
    print(f"\n✓ All repair embeddings generated and uploaded in {elapsed:.1f}s")
    print(f"  Average: {elapsed/len(repairs_df)*1000:.1f}ms per repair")

def test_vector_search(client, model, collection_name):
    """Test vector search with sample queries for parts"""
    
    test_queries = [
        "dishwasher not draining water",
        "refrigerator ice maker broken",
        "dishwasher leaking from bottom"
    ]
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        
        # Generate query embedding
        query_embedding = model.encode(query).tolist()
        
        # Search Qdrant
        results = client.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=3
        )
        
        print(f"Top 3 results:")
        for i, result in enumerate(results, 1):
            payload = result.payload
            score = result.score
            print(f"  {i}. {payload['part_name']} (Score: {score:.3f})")
            print(f"     {payload['brand']} - ${payload['part_price']}")
            print(f"     Appliance: {payload['appliance_type']}")

def test_vector_search_repairs(client, model, collection_name):
    """Test vector search with sample queries for repairs"""
    
    test_queries = [
        "how to fix dishwasher not cleaning dishes",
        "refrigerator too warm"
    ]
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        
        # Generate query embedding
        query_embedding = model.encode(query).tolist()
        
        # Search Qdrant
        results = client.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=2
        )
        
        print(f"Top 2 results:")
        for i, result in enumerate(results, 1):
            payload = result.payload
            score = result.score
            print(f"  {i}. {payload['title']} (Score: {score:.3f})")
            print(f"     Product: {payload['product']}")
            print(f"     Difficulty: {payload['difficulty']}")

def get_collection_stats(client, collection_name):
    """Get and display collection statistics"""
    try:
        info = client.get_collection(collection_name)
        
        print(f"\nCollection: {collection_name}")
        print(f"  Vectors: {info.points_count:,}")
        print(f"  Dimension: {info.config.params.vectors.size}")
        print(f"  Distance: {info.config.params.vectors.distance}")
        print(f"  Indexed fields: {len(info.payload_schema)} payload indexes")
    except Exception as e:
        # Handle pydantic validation errors (Qdrant client/server version mismatch)
        print(f"\nCollection: {collection_name}")
        print(f"  ⚠️  Could not fetch full stats (client version mismatch)")
        print(f"  Status: Collection created successfully")
        # Try to get point count using count API
        try:
            count_result = client.count(collection_name)
            print(f"  Vectors: {count_result.count:,}")
        except:
            pass

def main():
    print("="*70)
    print("STEP 2: Qdrant Vector Database Setup")
    print("="*70)
    
    try:
        # Initialize clients
        print("\nConnecting to Qdrant...")
        client = get_qdrant_client()
        print(f"✓ Connected to Qdrant at {os.getenv('QDRANT_HOST')}:{os.getenv('QDRANT_PORT')}")
        
        # Load embedding model
        model = load_embedding_model()
        
        # ============================================================
        # PARTS COLLECTION
        # ============================================================
        print("\n" + "="*70)
        print("PROCESSING PARTS")
        print("="*70)
        
        # Load parts from CSV
        parts_df = load_parts_from_csv()
        
        # Setup parts collection
        parts_collection = setup_qdrant_collection(
            client, model, 
            collection_name="partselect_parts",
            collection_type="parts"
        )
        
        # Generate and upload parts embeddings
        generate_and_upload_embeddings_parts(client, model, parts_collection, parts_df)
        
        # Get parts collection stats
        get_collection_stats(client, parts_collection)
        
        # ============================================================
        # REPAIRS COLLECTION
        # ============================================================
        print("\n" + "="*70)
        print("PROCESSING REPAIRS")
        print("="*70)
        
        # Load repairs from CSV
        repairs_df = load_repairs_from_csv()
        
        if repairs_df is not None and len(repairs_df) > 0:
            # Setup repairs collection
            repairs_collection = setup_qdrant_collection(
                client, model,
                collection_name="partselect_repairs",
                collection_type="repairs"
            )
            
            # Generate and upload repairs embeddings
            generate_and_upload_embeddings_repairs(client, model, repairs_collection, repairs_df)
            
            # Get repairs collection stats
            get_collection_stats(client, repairs_collection)
        else:
            print("  Skipping repairs collection (no data)")
        
        # ============================================================
        # TEST SEARCHES
        # ============================================================
        print("\n" + "="*70)
        print("TESTING VECTOR SEARCH")
        print("="*70)
        
        # Test parts search
        test_vector_search(client, model, parts_collection)
        
        # Test repairs search if available
        if repairs_df is not None and len(repairs_df) > 0:
            print("\n" + "-"*70)
            print("Testing Repairs Search:")
            print("-"*70)
            test_vector_search_repairs(client, model, repairs_collection)
        
        print("\n" + "="*70)
        print("✓ STEP 2 COMPLETE: Vector database setup successful!")
        print("="*70)
        print(f"\nCollections created:")
        print(f"  1. {parts_collection}: {len(parts_df):,} parts with payload indexes")
        if repairs_df is not None:
            print(f"  2. {repairs_collection}: {len(repairs_df):,} repairs with payload indexes")
        print("\nNext steps:")
        print("  1. View Qdrant dashboard: http://localhost:6333/dashboard")
        print("  2. Run: python backend/scripts/03_setup_tools.py")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
