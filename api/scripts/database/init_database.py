#!/usr/bin/env python3
"""
Initialize PostgreSQL database for Grace SaaS
Reads schema and creates all tables
"""

import os
import sys
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("❌ ERROR: DATABASE_URL not found in environment")
    print("Please add DATABASE_URL to .env file")
    sys.exit(1)

def init_database():
    """Initialize PostgreSQL database with schema"""

    print("🐘 Connecting to PostgreSQL...")

    try:
        # Parse sslmode from DATABASE_URL or default based on host
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(DATABASE_URL)
        query_params = parse_qs(parsed.query)
        
        # Default SSL mode: 'disable' for localhost, 'require' for remote
        hostname = parsed.hostname or 'localhost'
        is_local = hostname in ('localhost', '127.0.0.1', '::1')
        default_sslmode = 'disable' if is_local else 'require'
        
        sslmode = query_params.get('sslmode', [default_sslmode])[0]

        conn = psycopg2.connect(DATABASE_URL.split('?')[0], sslmode=sslmode)
        cursor = conn.cursor()

        print("✅ Connected to PostgreSQL")

        # Read schema file
        schema_path = "database/schema.sql"

        if not os.path.exists(schema_path):
            print(f"❌ Schema file not found: {schema_path}")
            sys.exit(1)

        print(f"📄 Reading schema from {schema_path}...")

        with open(schema_path, 'r') as f:
            schema_sql = f.read()

        # Execute schema
        print("🔨 Creating tables...")
        cursor.execute(schema_sql)
        conn.commit()

        print("✅ Database schema initialized!")

        # Verify tables created
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)

        tables = cursor.fetchall()

        print(f"\n📊 Created {len(tables)} tables:")
        for table in tables:
            print(f"   ✓ {table[0]}")

        cursor.close()
        conn.close()

        print("\n✅ Database initialization complete!")
        print("\nNext steps:")
        print("  1. Create first user:    python3 manage_users_pg.py add email@example.com password123 'Name'")
        print("  2. Start backend:        python3 grace_api.py")
        print("  3. Configure Stripe:     Add STRIPE_SECRET_KEY to .env")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_database()
