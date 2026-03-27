"""
Text Cleaning Module
Cleans raw PDF text and splits it into structured sentences/paragraphs.
"""

import re
import nltk

# Download required NLTK data (only needed once)
try:
    nltk.data.find("tokenizers/punkt_tab")
except LookupError:
    nltk.download("punkt_tab", quiet=True)


def clean_text(raw_text: str) -> str:
    """
    Clean raw PDF text by removing artifacts and normalizing whitespace.
    
    Args:
        raw_text: Raw text extracted from PDF
        
    Returns:
        Cleaned text
    """
    text = raw_text

    # Remove page numbers (standalone numbers on their own line)
    text = re.sub(r"\n\s*\d{1,4}\s*\n", "\n", text)

    # Remove common headers/footers patterns
    text = re.sub(r"\n\s*(Chapter|CHAPTER)\s*\n", "\n", text)

    # Fix hyphenated line breaks (e.g., "beau-\ntiful" → "beautiful")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

    # Replace multiple newlines with double newline (paragraph separator)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Replace single newlines (mid-paragraph line breaks) with spaces
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)

    # Normalize multiple spaces to single space
    text = re.sub(r" {2,}", " ", text)

    # Strip leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    # Remove empty lines at start and end
    text = text.strip()

    return text


def split_into_paragraphs(text: str) -> list[str]:
    """
    Split cleaned text into paragraphs.
    
    Args:
        text: Cleaned text
        
    Returns:
        List of paragraph strings
    """
    paragraphs = re.split(r"\n\n+", text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    return paragraphs


def split_into_sentences(text: str) -> list[str]:
    """
    Split text into individual sentences using NLTK.
    
    Args:
        text: Cleaned text (paragraph or full text)
        
    Returns:
        List of sentences
    """
    sentences = nltk.sent_tokenize(text)
    sentences = [s.strip() for s in sentences if s.strip()]

    return sentences


def process_text(raw_text: str) -> list[dict]:
    """
    Full text processing pipeline: clean → split into paragraphs → split into sentences.
    
    Args:
        raw_text: Raw text from PDF extraction
        
    Returns:
        List of dicts, each containing a paragraph and its sentences
    """
    cleaned = clean_text(raw_text)
    paragraphs = split_into_paragraphs(cleaned)

    result = []
    for i, paragraph in enumerate(paragraphs):
        sentences = split_into_sentences(paragraph)
        result.append({
            "paragraph_index": i,
            "text": paragraph,
            "sentences": sentences
        })

    return result
