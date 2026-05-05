from db.database import engine
from sqlalchemy import text

def init():
    with engine.begin() as conn:
        # Asosiy documents table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS documents (
                id SERIAL PRIMARY KEY,
                file_name TEXT,
                content TEXT,
                embedding JSONB
            );
        """))

        # Qaysi fayllar allaqachon ingest qilinganini track qilish
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ingested_files (
                id SERIAL PRIMARY KEY,
                file_name TEXT UNIQUE,
                ingested_at TIMESTAMP DEFAULT NOW()
            );
        """))

    print("✅ DB READY")

if __name__ == "__main__":
    init()