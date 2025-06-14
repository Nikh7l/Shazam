"""Migration to add background task tracking tables."""
import sqlite3

def migrate(db_path):
    """Run the migration"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create background_tasks table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS background_tasks (
        task_id TEXT PRIMARY KEY,
        task_type TEXT NOT NULL,
        spotify_url TEXT,
        status TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        started_at TIMESTAMP,
        completed_at TIMESTAMP,
        processed_items INTEGER DEFAULT 0,
        total_items INTEGER DEFAULT 1,
        result_json TEXT
    )
    """)
    
    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_status ON background_tasks(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_created ON background_tasks(created_at)")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python v2_add_task_tracking.py <db_path>")
        sys.exit(1)
    
    migrate(sys.argv[1])
