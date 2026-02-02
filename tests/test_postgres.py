"""
Test PostgreSQL Connection and Data
Quick script to verify data exists in PostgreSQL
"""

import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

print("Testing PostgreSQL connection...")
print(f"Host: {os.getenv('POSTGRES_HOST')}")
print(f"Port: {os.getenv('POSTGRES_PORT')}")
print(f"Database: {os.getenv('POSTGRES_DB')}")
print(f"User: {os.getenv('POSTGRES_USER')}")
print(f"Password: {'*' * len(os.getenv('POSTGRES_PASSWORD', ''))}\n")

try:
    # Connect using psycopg2 directly
    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=os.getenv('POSTGRES_PORT', '5432'),
        database=os.getenv('POSTGRES_DB', 'partselect'),
        user=os.getenv('POSTGRES_USER', 'postgres'),
        password=os.getenv('POSTGRES_PASSWORD', '')
    )
    
    print("✓ Connected to PostgreSQL!\n")
    
    cursor = conn.cursor()
    
    # Check if tables exist
    cursor.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public'
    """)
    tables = cursor.fetchall()
    print(f"Tables found: {[t[0] for t in tables]}\n")
    
    # Count rows in parts table
    cursor.execute('SELECT COUNT(*) FROM parts')
    count = cursor.fetchone()[0]
    print(f"Total parts in database: {count:,}\n")
    
    # Get first 3 rows
    cursor.execute('SELECT part_id, part_name, brand, part_price FROM parts LIMIT 3')
    rows = cursor.fetchall()
    print("First 3 parts:")
    for row in rows:
        print(f"  {row[0]}: {row[1]}")
        print(f"    Brand: {row[2]}, Price: ${row[3]}\n")
    
    # Count repairs
    cursor.execute('SELECT COUNT(*) FROM repairs')
    count = cursor.fetchone()[0]
    print(f"Total repair guides: {count}\n")
    
    # Get first 3 repairs
    cursor.execute('SELECT product, symptom, difficulty FROM repairs LIMIT 3')
    rows = cursor.fetchall()
    print("First 3 repair guides:")
    for row in rows:
        print(f"  {row[0]} - {row[1]}")
        print(f"    Difficulty: {row[2]}\n")
    
    cursor.close()
    conn.close()
    
    print("="*70)
    print("✓ SUCCESS! Data is in the database.")
    print("="*70)
    print("\nNow try connecting in pgAdmin with these credentials:")
    print(f"  Host: {os.getenv('POSTGRES_HOST')}")
    print(f"  Port: {os.getenv('POSTGRES_PORT')}")
    print(f"  Database: {os.getenv('POSTGRES_DB')}")
    print(f"  User: {os.getenv('POSTGRES_USER')}")
    print(f"  Password: {os.getenv('POSTGRES_PASSWORD')}")
    
except psycopg2.OperationalError as e:
    print("✗ CONNECTION FAILED!")
    print(f"Error: {e}\n")
    print("This means the password in your .env file doesn't match PostgreSQL.")
    print("\nTo fix this in pgAdmin:")
    print("1. Right-click on your server (PostgreSQL) in pgAdmin")
    print("2. Select 'Properties'")
    print("3. Go to 'Connection' tab")
    print("4. Check what password is saved there")
    print("5. Update your .env file with that password")

except Exception as e:
    print(f"✗ ERROR: {e}")
