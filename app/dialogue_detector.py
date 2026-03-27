"""
Dialogue Detection Module
Splits story text into dialogue and narration segments.
Handles all types of quotes: straight, curly/smart, and other Unicode variants.
"""

import re


# All possible quote characters (straight + curly + unicode)
OPEN_QUOTES = '"\u201c\u00ab\u2018'   # " " « '
CLOSE_QUOTES = '"\u201d\u00bb\u2019'  # " " » '
ALL_QUOTES = OPEN_QUOTES + CLOSE_QUOTES


def detect_segments(text: str) -> list[dict]:
    """
    Split text into dialogue and narration segments.
    
    Detects quoted speech using all quote styles and separates from narration.
    Also extracts attribution (e.g., "she said", "he whispered").
    """
    segments = []

    # Normalize smart quotes to straight quotes for consistent processing
    normalized = text
    for oq in OPEN_QUOTES:
        normalized = normalized.replace(oq, '"')
    for cq in CLOSE_QUOTES:
        normalized = normalized.replace(cq, '"')

    # Pattern: capture text before quote, the quoted dialogue, and attribution after
    dialogue_pattern = re.compile(
        r'"([^"]+?)"'       # Quoted dialogue
        r'([^"]*?'          # Attribution text after quote
        r'(?:[.!?,;]|$))'   # End at punctuation or end of string
    )

    last_end = 0

    for match in dialogue_pattern.finditer(normalized):
        start = match.start()

        # Capture narration before this dialogue
        before_text = normalized[last_end:start].strip()
        if before_text:
            segments.append({
                "type": "narration",
                "text": before_text
            })

        # Extract dialogue
        dialogue_text = match.group(1).strip()
        attribution = match.group(2).strip() if match.group(2) else ""

        # Detect speaker gender from attribution
        gender = detect_gender_from_attribution(attribution)

        segments.append({
            "type": "dialogue",
            "text": dialogue_text,
            "attribution": attribution,
            "speaker_gender": gender
        })

        last_end = match.end()

    # Capture any remaining narration after last dialogue
    remaining = normalized[last_end:].strip()
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
    """
    attr = attribution.lower()

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
        if indicator in attr:
            return "female"

    for indicator in male_indicators:
        if indicator in attr:
            return "male"

    return "unknown"


def process_paragraphs(paragraphs: list[dict]) -> list[dict]:
    """
    Process a list of paragraph dicts and detect dialogue in each.
    """
    total_dialogue = 0
    total_narration = 0

    for paragraph in paragraphs:
        paragraph["segments"] = detect_segments(paragraph["text"])
        for seg in paragraph["segments"]:
            if seg["type"] == "dialogue":
                total_dialogue += 1
            else:
                total_narration += 1

    print(f"  Dialogue segments: {total_dialogue}, Narration segments: {total_narration}")
    return paragraphs
