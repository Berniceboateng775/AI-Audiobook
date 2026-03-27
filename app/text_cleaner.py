"""
Text Cleaning Module
Cleans raw PDF text, removes front matter, and splits into structured paragraphs.
"""

import re
import nltk

# Download required NLTK data (only needed once)
try:
    nltk.data.find("tokenizers/punkt_tab")
except LookupError:
    nltk.download("punkt_tab", quiet=True)


# Front matter patterns to SKIP entirely (copyright, dedication, etc.)
FRONT_MATTER_PATTERNS = [
    r"(?i)all rights reserved",
    r"(?i)copyright\s*©",
    r"(?i)isbn[\s:\-]",
    r"(?i)published\s+by",
    r"(?i)printed\s+in",
    r"(?i)library\s+of\s+congress",
    r"(?i)first\s+edition",
    r"(?i)cover\s+design",
    r"(?i)editing\s+by",
    r"(?i)no\s+part\s+of\s+this",
    r"(?i)reproduction\s+or\s+transmission",
    r"(?i)table\s+of\s+contents",
    r"(?i)also\s+by\s+\w+",
    r"(?i)other\s+books?\s+by",
    r"(?i)newsletter",
    r"(?i)join\s+my\s+(mailing|reader)",
    r"(?i)follow\s+me\s+on",
    r"(?i)acknowledgments",
    r"(?i)about\s+the\s+author",
    r"(?i)connect\s+with",
]

# Heading/title patterns — short lines that look like section headers
HEADING_PATTERN = re.compile(
    r"^(chapter|prologue|epilogue|part)\s*\d*\s*[:.\-]?\s*(.*)$",
    re.IGNORECASE
)


def is_front_matter(text: str) -> bool:
    """Check if a paragraph is front matter (copyright, etc.) that should be skipped."""
    for pattern in FRONT_MATTER_PATTERNS:
        if re.search(pattern, text):
            return True
    return False


def is_heading(text: str) -> bool:
    """Check if text is likely a chapter heading or title."""
    text = text.strip()
    # Very short text (1-8 words) in mostly uppercase or matching heading pattern
    words = text.split()
    if len(words) <= 8:
        if text.isupper() or HEADING_PATTERN.match(text):
            return True
        # Single-word or very short lines that look like titles
        if len(words) <= 3 and not any(c in text for c in '.!?"'):
            return True
    return False


def clean_text(raw_text: str) -> str:
    """Clean raw PDF text by removing artifacts and normalizing whitespace."""
    text = raw_text

    # Remove page numbers
    text = re.sub(r"\n\s*\d{1,4}\s*\n", "\n", text)

    # Fix hyphenated line breaks
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

    # Replace multiple newlines with double newline (paragraph separator)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Replace single newlines (mid-paragraph line breaks) with spaces
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)

    # Normalize multiple spaces
    text = re.sub(r" {2,}", " ", text)

    # Strip whitespace from each line
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    text = text.strip()
    return text


def split_into_paragraphs(text: str) -> list[str]:
    """Split cleaned text into paragraphs."""
    paragraphs = re.split(r"\n\n+", text)
    return [p.strip() for p in paragraphs if p.strip()]


def split_into_sentences(text: str) -> list[str]:
    """Split text into individual sentences using NLTK."""
    sentences = nltk.sent_tokenize(text)
    return [s.strip() for s in sentences if s.strip()]


def process_text(raw_text: str) -> list[dict]:
    """
    Full text processing pipeline:
    - Clean text
    - Remove front matter (copyright, etc.)
    - Detect headings and mark them
    - Split into paragraphs and sentences
    """
    cleaned = clean_text(raw_text)
    paragraphs = split_into_paragraphs(cleaned)

    result = []
    front_matter_done = False
    
    for i, paragraph in enumerate(paragraphs):
        # Skip front matter at the beginning of the book
        if not front_matter_done:
            if is_front_matter(paragraph):
                continue
            # Once we find a paragraph that isn't front matter, stop checking
            # (only skip front matter at the very start)
            if len(paragraph) > 100:
                front_matter_done = True
        
        # Skip very short paragraphs that are just noise
        if len(paragraph.strip()) < 3:
            continue
        
        sentences = split_into_sentences(paragraph)
        
        para_dict = {
            "paragraph_index": len(result),
            "text": paragraph,
            "sentences": sentences,
        }
        
        # Mark headings so voice engine can handle them differently
        if is_heading(paragraph):
            para_dict["is_heading"] = True
        
        result.append(para_dict)

    skipped = len(paragraphs) - len(result)
    if skipped > 0:
        print(f"  Skipped {skipped} front matter/noise paragraphs")

    return result
