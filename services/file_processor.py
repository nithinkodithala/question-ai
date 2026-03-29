import fitz  # PyMuPDF
from docx import Document
import io

from utils.text_cleaning import clean_text

def extract_text_from_pdf(content: bytes) -> str:
    """Extract text from PDF using PyMuPDF."""
    text = ""
    try:
        with fitz.open(stream=content, filetype="pdf") as doc:
            for page in doc:
                text += page.get_text()
    except Exception as e:
        print(f"Error extracting PDF: {e}")
        return ""
    return clean_text(text)

def extract_text_from_docx(content: bytes) -> str:
    """Extract text from DOCX using python-docx."""
    text = ""
    try:
        doc = Document(io.BytesIO(content))
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception as e:
        print(f"Error extracting DOCX: {e}")
        return ""
    return clean_text(text)

def extract_text(filename: str, content: bytes) -> str:
    """General text extraction for supported file types."""
    if filename.lower().endswith('.pdf'):
        return extract_text_from_pdf(content)
    elif filename.lower().endswith(('.docx', '.doc')):
        return extract_text_from_docx(content)
    return ""
