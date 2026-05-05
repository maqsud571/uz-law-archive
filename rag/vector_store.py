import numpy as np
import json
from sqlalchemy import text
from db.database import engine
from rag.embedder import get_embedding


def search(query: str, top_k: int = 5):
    """Vector similarity bo'yicha qidirish — barcha fayllardan"""
    q_vec = np.array(get_embedding(query))

    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT file_name, content, embedding FROM documents")
        ).fetchall()

    results = []

    for row in rows:
        db_vec = row.embedding

        if isinstance(db_vec, str):
            db_vec = json.loads(db_vec)

        db_vec = np.array(db_vec)

        score = np.dot(q_vec, db_vec) / (
            np.linalg.norm(q_vec) * np.linalg.norm(db_vec)
        )

        results.append((row.file_name, row.content, float(score)))

    results.sort(key=lambda x: x[2], reverse=True)

    return [(file_name, content) for file_name, content, _ in results[:top_k]]


def search_exact(article_number: str, top_k: int = 5):
    """Modda raqami bo'yicha aniq qidirish — barcha fayllardan"""
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT file_name, content 
                FROM documents
                WHERE content ILIKE :pattern
                LIMIT :limit
            """),
            {
                "pattern": f"%{article_number}-modda%",
                "limit": top_k
            }
        ).fetchall()

    return [(r[0], r[1]) for r in rows]