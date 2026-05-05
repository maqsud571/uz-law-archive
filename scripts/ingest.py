import os
import json
import re
from sqlalchemy import text

from db.database import engine
from rag.pdf_loader import load_pdf
from rag.embedder import get_embedding
from utils.log import logger

DATA_FOLDER = "data"
MIN_CHUNK_LEN = 200  # Bundan qisqa chunklar saqlanmaydi

# DB yordamchi funksiyalar

def is_already_ingested(file_name: str) -> bool:
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT 1 FROM ingested_files WHERE file_name = :f"),
            {"f": file_name}
        ).fetchone()
    return result is not None


def mark_as_ingested(file_name: str):
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO ingested_files (file_name) VALUES (:f) ON CONFLICT DO NOTHING"),
            {"f": file_name}
        )


def save_chunk(file, chunk, embedding):
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO documents (file_name, content, embedding)
            VALUES (:f, :c, :e)
        """), {"f": file, "c": chunk, "e": json.dumps(embedding)})


# MATN TOZALASH
# lex.uz dan yuklangan PDF larda
# har sahifada timestamp, URL, "Oldingi tahrirga qarang" qatorlari bor

def clean_text(text: str) -> str:
    lines = text.split('\n')
    cleaned = []

    for line in lines:
        line = line.strip()

        # Bo'sh qatorlar
        if not line:
            continue

        # Timestamp: "05.05.2026, 16:32 ..."
        if re.match(r'\d{2}\.\d{2}\.\d{4},\s*\d{2}:\d{2}', line):
            continue

        # URL qatorlar: "https://www.lex.uz/docs/..."
        if re.match(r'https?://', line):
            continue

        # Sahifa raqami: "1/259", "2/231"
        if re.match(r'^\d+/\d+$', line):
            continue

        # "Oldingi tahrirga qarang."
        if re.match(r'^Oldingi tahrirga qarang', line, re.IGNORECASE):
            continue

        # Havola qatorlar: "(3-moddaning birinchi qismi ... Qonuni tahririda ...)"
        # Bular qonun o'zgarishiga havola — mazmuniy emas
        if re.match(r'^\(\d+[-\u2013]moddan', line, re.IGNORECASE):
            continue
        if re.match(r'^\(\d+[-\u2013]modda\s+O', line, re.IGNORECASE):
            continue

        cleaned.append(line)

    return '\n'.join(cleaned)

# MODDA BO'YICHA SPLIT (Kodekslar uchun)
# Har bir modda sarlavhasi + mazmuni = 1 chunk

def split_by_articles(text: str) -> list[str]:
    pattern = r'(\d+[-\u2013]\s*modda\.?\s+[^\n]+)'

    parts = re.split(r'(?=\d+[-\u2013]\s*modda)', text)

    chunks = []
    for part in parts:
        part = part.strip()
        if len(part) >= MIN_CHUNK_LEN:
            chunks.append(part)

    return chunks


def split_by_paragraphs(text: str, size: int = 1200, overlap: int = 200) -> list[str]:
    # Avval bob sarlavhalarida ajrat
    bob_pattern = r'(?=\n[IVX]+\s+bob\b|^\d+[-\u2013]?\s*bob\b)'
    sections = re.split(bob_pattern, text, flags=re.IGNORECASE | re.MULTILINE)

    chunks = []
    for section in sections:
        section = section.strip()
        if not section:
            continue

        # Har bir bobni size ga bo'lib chunk qilamiz
        if len(section) <= size:
            if len(section) >= MIN_CHUNK_LEN:
                chunks.append(section)
        else:
            start = 0
            while start < len(section):
                end = start + size
                # So'z o'rtasida kesmaslik uchun oxirgi \n ni topamiz
                if end < len(section):
                    cut = section.rfind('\n', start, end)
                    if cut > start:
                        end = cut
                chunk = section[start:end].strip()
                if len(chunk) >= MIN_CHUNK_LEN:
                    chunks.append(chunk)
                start = end - overlap

    return chunks


def smart_split(file_name: str, text: str) -> list[str]:
    # Avval tozalash
    text = clean_text(text)

    # Modda soni hisoblaymiz
    modda_count = len(re.findall(r'\d+[-\u2013]\s*modda', text, re.IGNORECASE))
    total_chars = len(text)

    logger.info(f"  📊 {file_name}: {modda_count} modda, {total_chars:,} belgi")

    # Agar moddalar ko'p bo'lsa → kodeks → modda bo'yicha split
    if modda_count >= 10:
        logger.info(f"  → 📜 KODEKS rejimi: modda bo'yicha split")
        return split_by_articles(text)
    else:
        # Darslik / sharh → paragraf bo'yicha
        logger.info(f"  → 📚 DARSLIK rejimi: paragraf bo'yicha split")
        return split_by_paragraphs(text)


def read_files():
    docs = []
    for f in sorted(os.listdir(DATA_FOLDER)):
        path = os.path.join(DATA_FOLDER, f)
        if f.endswith(".txt"):
            with open(path, "r", encoding="utf-8") as file:
                docs.append((f, file.read()))
        elif f.endswith(".pdf"):
            docs.append((f, load_pdf(path)))
    return docs


# ASOSIY INGEST

def ingest():
    docs = read_files()
    logger.info(f"📁 {len(docs)} ta fayl topildi")

    total_new = 0
    skipped = 0

    for file, content in docs:
        if is_already_ingested(file):
            logger.info(f"⏭️  {file} — allaqachon ingest qilingan")
            skipped += 1
            continue

        logger.info(f"⚙️  {file} ishlanmoqda...")
        chunks = smart_split(file, content)
        logger.info(f"  ✂️  {len(chunks)} ta chunk hosil bo'ldi")

        for i, chunk in enumerate(chunks):
            emb = get_embedding(chunk)
            save_chunk(file, chunk, emb)
            total_new += 1

            if (i + 1) % 50 == 0:
                logger.info(f"  💾 {i+1}/{len(chunks)} saqlandi...")

        mark_as_ingested(file)
        logger.info(f"✅ {file} — {len(chunks)} chunk saqlandi")

    logger.info(f"\n📊 NATIJA: {total_new} ta yangi chunk | {skipped} ta fayl o'tkazildi")


if __name__ == "__main__":
    ingest()