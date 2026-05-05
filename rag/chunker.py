def chunk_text(text, size=500, overlap=100):
    chunks = []
    start = 0

    while start < len(text):
        chunks.append(text[start:start+size])
        start += size - overlap

    return chunks