"""
Dialogue Detection Module
Splits story text into dialogue and narration segments.
Identifies quoted speech and attribution tags.
"""

import re


def detect_segments(text: str) -> list[dict]:
    """
    Split text into dialogue and narration segments.
    
    Detects quoted speech (using "" or "") and separates it from narration.
    Also extracts attribution (e.g., "she said", "he whispered").
    
    Args:
        text: Cleaned story text
        
    Returns:
        List of segment dicts with type, text, and optional attribution
    """
    segments = []

    # Pattern to match quoted dialogue with optional attribution
    # Handles: "text" | "text" | "text"
    dialogue_pattern = re.compile(
        r'(?P<before>[^"""\n]*?)'           # narration before quote
        r'["""]'                              # opening quote
        r'(?P<dialogue>[^"""]+?)'            # dialogue content
        r'["""]'                              # closing quote
        r'(?P<attribution>[^"""\n.!?]*[.!?]?)' # attribution after quote
    )

    last_end = 0

    for match in dialogue_pattern.finditer(text):
        start = match.start()

        # Capture narration before this dialogue
        before_text = text[last_end:start].strip()
        if before_text:
            # Also add any "before" group text
            combined_before = before_text
            if match.group("before").strip():
                combined_before = before_text
            segments.append({
                "type": "narration",
                "text": combined_before
            })
        elif match.group("before").strip():
            segments.append({
                "type": "narration",
                "text": match.group("before").strip()
            })

        # Extract dialogue
        dialogue_text = match.group("dialogue").strip()
        attribution = match.group("attribution").strip() if match.group("attribution") else ""

        # Detect speaker gender from attribution
        gender = detect_gender_from_attribution(attribution)

        segment = {
            "type": "dialogue",
            "text": dialogue_text,
            "attribution": attribution,
            "speaker_gender": gender
        }
        segments.append(segment)

        # If there's attribution text, add it as narration too (for the narrator to read)
        if attribution and len(attribution) > 3:
            segments.append({
                "type": "narration",
                "text": attribution
            })

        last_end = match.end()

    # Capture any remaining narration after last dialogue
    remaining = text[last_end:].strip()
    if remaining:
        segments.append({
            "type": "narration",
            "text": remaining
        })

    # If no dialogue was found, return the whole text as narration
    if not segments:
        segments.append({
            "type": "narration",
            "text": text.strip()
        })

    return segments


def detect_gender_from_attribution(attribution: str) -> str:
    """
    Detect speaker gender from attribution text using keyword rules.
    
    Args:
        attribution: Text like "she said", "he whispered"
        
    Returns:
        "male", "female", or "unknown"
    """
    attribution_lower = attribution.lower()

    female_indicators = [
        "she ", "her ", "hers", "woman", "girl", "lady",
        "mother", "sister", "daughter", "queen", "princess",
        "madam", "miss", "mrs", "mama", "mom"
    ]

    male_indicators = [
        "he ", "his ", "him ", "man", "boy", "gentleman",
        "father", "brother", "son", "king", "prince",
        "sir", "mr", "papa", "dad"
    ]

    for indicator in female_indicators:
        if indicator in attribution_lower:
            return "female"

    for indicator in male_indicators:
        if indicator in attribution_lower:
            return "male"

    return "unknown"


def process_paragraphs(paragraphs: list[dict]) -> list[dict]:
    """
    Process a list of paragraph dicts and detect dialogue in each.
    
    Args:
        paragraphs: Output from text_cleaner.process_text()
        
    Returns:
        List of paragraph dicts with added 'segments' field
    """
    for paragraph in paragraphs:
        paragraph["segments"] = detect_segments(paragraph["text"])

    return paragraphs
