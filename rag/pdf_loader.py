import pdfplumber

def load_pdf(path: str):
    text = ""

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""

    return text