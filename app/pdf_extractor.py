"""
PDF Text Extraction Module
Extracts clean text from PDF storybooks using PyMuPDF.
"""

import fitz  # PyMuPDF


def extract_text(pdf_path: str) -> str:
    """
    Extract all text from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Raw text content from all pages
    """
    doc = fitz.open(pdf_path)
    full_text = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")

        if text.strip():
            full_text.append(text)

    doc.close()

    return "\n".join(full_text)


def extract_text_by_pages(pdf_path: str) -> list[dict]:
    """
    Extract text from a PDF file, organized by page.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        List of dicts with page_number and text
    """
    doc = fitz.open(pdf_path)
    pages = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")

        if text.strip():
            pages.append({
                "page_number": page_num + 1,
                "text": text.strip()
            })

    doc.close()

    return pages


def get_pdf_metadata(pdf_path: str) -> dict:
    """
    Extract metadata from a PDF file (title, author, etc.)
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Dictionary of PDF metadata
    """
    doc = fitz.open(pdf_path)
    metadata = doc.metadata
    metadata["page_count"] = len(doc)
    doc.close()

    return metadata
