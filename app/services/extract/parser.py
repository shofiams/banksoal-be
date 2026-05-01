import os
import pdfplumber
from docx import Document

# proses extract file / parse dokumen
def parse_document(file_path):
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        return parse_pdf(file_path)
    elif ext == ".docx":
        return parse_docx(file_path)
    else:
        raise ValueError("Format file tidak didukung")

# parse pdf
def parse_pdf(file_path):
    pages = []
    with pdfplumber.open(file_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            pages.append((i + 1, text))
    return pages

# parse docx
def parse_docx(file_path):
    doc = Document(file_path)
    full_text = "\n".join([p.text for p in doc.paragraphs])
    return [(1, full_text)]
