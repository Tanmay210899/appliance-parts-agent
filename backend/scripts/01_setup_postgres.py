"""
Step 1: PostgreSQL Database Setup
Load CSV data into PostgreSQL database
"""

import pandas as pd
from sqlalchemy import create_engine, text
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_db_url():
    """Construct database URL from environment variables"""
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "partselect")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "")
    
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"

def create_tables(engine):
    """Create database tables"""
    
    print("Creating tables...")
    
    # Parts table - stores all structured part data
    create_parts_table = """
    DROP TABLE IF EXISTS parts CASCADE;
    
    CREATE TABLE parts (
        part_id VARCHAR(50) PRIMARY KEY,
        part_name TEXT NOT NULL,
        mpn_id VARCHAR(100),
        brand VARCHAR(100),
        part_price DECIMAL(10,2),
        availability VARCHAR(50),
        install_difficulty VARCHAR(50),
        install_time VARCHAR(50),
        product_types TEXT,
        symptoms TEXT,
        replace_parts TEXT,
        product_description TEXT,
        installation_story TEXT,
        install_video_url TEXT,
        product_url TEXT NOT NULL,
        appliance_type VARCHAR(50) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Indexes for fast searching
    CREATE INDEX idx_parts_appliance ON parts(appliance_type);
    CREATE INDEX idx_parts_brand ON parts(brand);
    CREATE INDEX idx_parts_symptoms ON parts USING gin(to_tsvector('english', symptoms));
    CREATE INDEX idx_parts_replace ON parts USING gin(to_tsvector('english', replace_parts));
    """
    
    # Repairs table - stores repair guides
    create_repairs_table = """
    DROP TABLE IF EXISTS repairs CASCADE;
    
    CREATE TABLE repairs (
        id SERIAL PRIMARY KEY,
        product VARCHAR(50) NOT NULL,
        symptom VARCHAR(200) NOT NULL,
        description TEXT,
        percentage INTEGER,
        parts TEXT,
        symptom_detail_url TEXT,
        difficulty VARCHAR(50),
        repair_video_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Indexes
    CREATE INDEX idx_repairs_product ON repairs(product);
    CREATE INDEX idx_repairs_symptom ON repairs(symptom);
    """
    
    with engine.connect() as conn:
        conn.execute(text(create_parts_table))
        conn.execute(text(create_repairs_table))
        conn.commit()
    
    print("✓ Tables created successfully")

def load_parts_data(engine):
    """Load parts CSV data into database"""
    
    data_dir = Path(__file__).parent.parent.parent / "data"
    
    print("\nLoading parts data...")
    
    # Load dishwasher parts
    print("  Loading dishwasher parts...")
    df_dish = pd.read_csv(data_dir / "dishwasher_parts.csv")
    df_dish['appliance_type'] = 'Dishwasher'
    
    # Include all columns - descriptions needed for vector embeddings
    parts_columns = [
        'part_id', 'part_name', 'mpn_id', 'brand', 'part_price', 
        'availability', 'install_difficulty', 'install_time', 
        'product_types', 'symptoms', 'replace_parts', 
        'product_description', 'installation_story',
        'install_video_url', 'product_url', 'appliance_type'
    ]
    
    df_dish = df_dish[parts_columns]
    # Use 'replace' to ensure clean table creation
    df_dish.to_sql('parts', engine, if_exists='replace', index=False, method='multi', chunksize=100)
    print(f"  ✓ Loaded {len(df_dish):,} dishwasher parts")
    
    # Load refrigerator parts
    print("  Loading refrigerator parts...")
    df_fridge = pd.read_csv(data_dir / "refrigerator_parts.csv")
    df_fridge['appliance_type'] = 'Refrigerator'
    df_fridge = df_fridge[parts_columns]
    df_fridge.to_sql('parts', engine, if_exists='append', index=False, method='multi', chunksize=100)
    print(f"  ✓ Loaded {len(df_fridge):,} refrigerator parts")
    
    print(f"\n✓ Total parts loaded: {len(df_dish) + len(df_fridge):,}")

def load_repairs_data(engine):
    """Load repairs CSV data into database"""
    
    data_dir = Path(__file__).parent.parent.parent / "data"
    
    print("\nLoading repairs data...")
    
    # Load dishwasher repairs
    df_dish_repairs = pd.read_csv(data_dir / "dishwasher_repairs.csv")
    # Normalize column names to lowercase
    df_dish_repairs.columns = df_dish_repairs.columns.str.lower()
    df_dish_repairs.to_sql('repairs', engine, if_exists='replace', index=False)
    print(f"  ✓ Loaded {len(df_dish_repairs)} dishwasher repairs")
    
    # Load refrigerator repairs
    df_fridge_repairs = pd.read_csv(data_dir / "refrigerator_repairs.csv")
    df_fridge_repairs.columns = df_fridge_repairs.columns.str.lower()
    df_fridge_repairs.to_sql('repairs', engine, if_exists='append', index=False)
    print(f"  ✓ Loaded {len(df_fridge_repairs)} refrigerator repairs")
    
    print(f"\n✓ Total repairs loaded: {len(df_dish_repairs) + len(df_fridge_repairs)}")

def test_queries(engine):
    """Test some basic queries"""
    
    print("\n" + "="*70)
    print("Testing database queries...")
    print("="*70)
    
    with engine.connect() as conn:
        # Test 1: Count parts
        result = conn.execute(text("SELECT COUNT(*) FROM parts"))
        count = result.scalar()
        print(f"\n1. Total parts in database: {count:,}")
        
        # Test 2: Parts by appliance
        result = conn.execute(text("""
            SELECT appliance_type, COUNT(*) as count 
            FROM parts 
            GROUP BY appliance_type
        """))
        print("\n2. Parts by appliance:")
        for row in result:
            print(f"   {row[0]}: {row[1]:,}")
        
        # Test 3: Sample part lookup
        result = conn.execute(text("""
            SELECT part_id, part_name, brand, part_price 
            FROM parts 
            LIMIT 3
        """))
        print("\n3. Sample parts:")
        for row in result:
            print(f"   {row[0]}: {row[1]} - ${row[3]} ({row[2]})")
        
        # Test 4: Symptom search
        result = conn.execute(text("""
            SELECT part_id, part_name, symptoms 
            FROM parts 
            WHERE symptoms ILIKE '%leaking%' 
            LIMIT 3
        """))
        print("\n4. Parts for 'leaking' symptom:")
        for row in result:
            print(f"   {row[0]}: {row[1]}")
        
        # Test 5: Repairs count
        result = conn.execute(text("SELECT COUNT(*) FROM repairs"))
        count = result.scalar()
        print(f"\n5. Total repair guides: {count}")
        
    print("\n" + "="*70)
    print("✓ All tests passed!")
    print("="*70)

def main():
    """Main setup function"""
    
    print("="*70)
    print("STEP 1: PostgreSQL Database Setup")
    print("="*70)
    
    # Get database URL
    db_url = get_db_url()
    print(f"\nConnecting to: {db_url.split('@')[1]}")  # Hide password
    
    try:
        # Create engine
        engine = create_engine(db_url)
        
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✓ Database connection successful\n")
        
        # Create tables
        create_tables(engine)
        
        # Load data
        load_parts_data(engine)
        load_repairs_data(engine)
        
        # Test queries
        test_queries(engine)
        
        print("\n" + "="*70)
        print("✓ STEP 1 COMPLETE: Database setup successful!")
        print("="*70)
        print("\nNext steps:")
        print("  1. Verify data in your PostgreSQL client")
        print("  2. Run: python backend/scripts/02_setup_qdrant.py")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("\nMake sure PostgreSQL is running and .env is configured correctly")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
