import re
from rag.vector_store import search, search_exact


def extract_article_number(query: str):
    match = re.search(r"\d+", query)
    return match.group() if match else None


def get_context(query: str):
    """
    Barcha PDF hujjatlardan kontekst yig'adi.
    Qaytaradi: (context_text, sources_list)
    """
    article_number = extract_article_number(query)
    results = []

    # 1. ANIQ QIDIRISH (modda raqami bo'lsa)
    if article_number:
        exact = search_exact(article_number)
        if exact:
            results = exact

    # 2. VECTOR QIDIRISH (har doim)
    vector_results = search(query)

    # Dublikatlarni olib tashlab birlashtirish
    seen = {content for _, content in results}
    for file_name, content in vector_results:
        if content not in seen:
            results.append((file_name, content))
            seen.add(content)

    # Kontekstni formatlash — qaysi hujjatdan kelgani bilan
    context_parts = []
    for file_name, content in results:
        doc_label = file_name.replace(".pdf", "").replace(".txt", "").replace("_", " ").upper()
        context_parts.append(f"[{doc_label}]\n{content}")

    context = "\n\n---\n\n".join(context_parts)
    sources = list({file_name for file_name, _ in results})

    return context, sources