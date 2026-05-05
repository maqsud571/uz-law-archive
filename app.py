from fastapi import FastAPI
from rag.chain import answer_question

app = FastAPI(title="O'zbekiston Huquqiy Assistant")


@app.get("/ask")
def ask(q: str):
    answer = answer_question(q)
    return {"answer": answer}


@app.get("/")
def root():
    return {"message": "O'zbekiston Huquqiy RAG Assistant ishga tushdi ✅"}