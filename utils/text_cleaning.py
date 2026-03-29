import re

def clean_text(text: str) -> str:
    """Basic text cleaning for extracted document content."""
    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text)
    # Remove multiple newlines
    text = re.sub(r'\n+', '\n', text)
    return text.strip()
