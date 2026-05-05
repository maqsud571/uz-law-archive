import os
from google import genai
from rag.retriever import get_context
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Model fallback tartibi
MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-flash-latest",
]

def generate_with_fallback(prompt: str) -> str:
    """Agar asosiy model band bo'lsa, keyingisiga o'tadi"""
    last_error = None
    for model in MODELS:
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt
            )
            return response.text
        except Exception as e:
            last_error = e
            continue
    raise last_error


def answer_question(query: str):
    context, sources = get_context(query)

    prompt = f"""
Siz O'zbekiston qonunchiligini yaxshi biladigan professional YURIST assistantisiz.
Fuqarolar sizga hayotiy muammolari bilan murojaat qiladi — siz ularni huquqiy jihatdan yo'naltirasiz.

QOIDALAR:
1. Avval fuqaroning muammosini oddiy tilda tushuntirib bering (huquqiy ta'rifi)
2. Qonun/modda boyicha huquqlari nima ekanini ayting
3. Qanday qadamlar tashlashi kerakligini aytib bering (qayerga borish, nima qilish)
4. Tegishli moddalar va qonunlardan misol keltiring
5. Javob oxirida qaysi hujjatdan foydalanganingizni ayting

MUHIM:
- Savol hayotiy tilda bolsa ham (masalan "uyimni tunab ketishdi"), huquqiy ekvivalentini toping ("ogirlik", "mol-mulkka tajovuz" va h.k.)
- Konkret modda raqamlari keltiring
- Oddiy, tushunarli tilda gapiring — murakkab yuridik atamalarni izohlang
- Agar kontekstda yetarli malumot bolmasa ham, umumiy yonalish bering

KONTEKST (huquqiy hujjatlardan):
--------------------
{context}
--------------------

FUQARO SAVOLI: {query}

YURIST JAVOBI:
"""

    answer = generate_with_fallback(prompt)

    if sources:
        source_labels = [s.replace(".pdf", "").replace(".txt", "").replace("_", " ") for s in sources]
        answer += f"\n\n📚 **Manbalar:** {', '.join(source_labels)}"

    return answer