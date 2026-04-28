import os
import sys
from dotenv import load_dotenv
import psycopg2

# Load environment variables
load_dotenv()
DB_USER = os.getenv("DB_ROOT_USER")
DB_PASS = os.getenv("DB_ROOT_PASSWORD")

if not DB_USER or not DB_PASS:
    print("❌ Error: DB_ROOT_USER or DB_ROOT_PASSWORD not found in environment variables.")
    sys.exit(1)

DB_PORT = os.getenv("DB_PORT", "5433")
CONN_STR = f"postgresql://{DB_USER}:{DB_PASS}@localhost:{DB_PORT}/pcb_aoi_db"

def reset_database():
    print("⚠️  WARNING: This will ERASE ALL DATA from 'runs' and 'images' tables!")
    confirm = input("Are you sure you want to proceed? (yes/no): ").strip().lower()
    
    if confirm != "yes":
        print("❌ Operation cancelled.")
        return

    try:
        conn = psycopg2.connect(CONN_STR)
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("🗑️  Truncating tables...")
        cursor.execute("TRUNCATE TABLE runs, images CASCADE;")
        
        print("✅ Database reset successfully! All data has been cleared.")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error resetting database: {e}")

if __name__ == "__main__":
    reset_database()
