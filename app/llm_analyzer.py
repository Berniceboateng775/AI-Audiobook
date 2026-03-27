"""
LLM Analyzer Module
Uses Ollama (local free LLM) to analyze text for:
- Character/speaker identification
- Emotion detection
- Scene mood classification
"""

import json
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "mistral"


def analyze_segment(segment: dict, model: str = DEFAULT_MODEL) -> dict:
    """
    Use Ollama LLM to analyze a text segment for emotion, speaker, and scene mood.
    
    Args:
        segment: Dict with 'type' and 'text' keys
        model: Ollama model name (default: "mistral")
        
    Returns:
        Enriched segment dict with emotion, speaker_gender, and scene_mood
    """
    text = segment["text"]
    segment_type = segment.get("type", "narration")

    prompt = f"""You are a story analyzer. Analyze this text segment and return ONLY valid JSON.

Text: "{text}"
Type: {segment_type}

Return this exact JSON structure (no other text):
{{
    "speaker_gender": "male" or "female" or "narrator",
    "emotion": one of ["neutral", "anger", "sadness", "love", "fear", "excitement", "humor", "suspense"],
    "emotion_intensity": "low" or "medium" or "high",
    "scene_mood": one of ["calm", "romantic", "action", "suspense", "dramatic", "humorous"],
    "speaking_style": one of ["normal", "whisper", "shout", "trembling", "sarcastic", "seductive", "cold"]
}}

Rules:
- For narration, speaker_gender is always "narrator"
- Detect emotion from context, not just words
- Be specific about speaking_style based on the text
"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Low temperature for consistent output
                    "num_predict": 200
                }
            },
            timeout=30
        )
        response.raise_for_status()

        result_text = response.json().get("response", "")
        analysis = parse_llm_response(result_text)

        # Merge LLM analysis with existing segment data
        enriched = {**segment, **analysis}

        # Preserve rule-based gender detection if LLM says "narrator" for dialogue
        if segment_type == "dialogue" and segment.get("speaker_gender") != "unknown":
            enriched["speaker_gender"] = segment["speaker_gender"]

        return enriched

    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        print(f"LLM analysis failed: {e}")
        return apply_fallback_analysis(segment)


def parse_llm_response(response_text: str) -> dict:
    """
    Parse JSON from LLM response, handling common formatting issues.
    
    Args:
        response_text: Raw text response from Ollama
        
    Returns:
        Parsed analysis dict
    """
    # Try to find JSON in the response
    text = response_text.strip()

    # Try direct JSON parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to extract JSON from markdown code block
    json_match = None
    import re
    patterns = [
        r"```json\s*(.*?)\s*```",
        r"```\s*(.*?)\s*```",
        r"\{.*\}"
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1) if "```" in pattern else match.group())
            except (json.JSONDecodeError, IndexError):
                continue

    # Return defaults if parsing fails
    return get_defaults()


def apply_fallback_analysis(segment: dict) -> dict:
    """
    Apply simple rule-based analysis when LLM is unavailable.
    
    Args:
        segment: Text segment dict
        
    Returns:
        Segment with fallback analysis fields
    """
    text = segment["text"].lower()
    defaults = get_defaults()

    # Simple emotion detection from keywords
    emotion_keywords = {
        "anger": ["angry", "furious", "rage", "hate", "shouted", "yelled", "screamed"],
        "sadness": ["sad", "cried", "tears", "sobbed", "grief", "mourning", "wept"],
        "love": ["love", "kiss", "embrace", "heart", "darling", "tender", "caress"],
        "fear": ["afraid", "scared", "terrified", "trembled", "horror", "panic", "shook"],
        "excitement": ["excited", "thrilled", "jumped", "laughed", "grinned", "amazing"],
        "suspense": ["slowly", "crept", "shadow", "silence", "watched", "waited", "dark"],
    }

    for emotion, keywords in emotion_keywords.items():
        if any(kw in text for kw in keywords):
            defaults["emotion"] = emotion
            break

    # Simple speaking style detection
    style_keywords = {
        "whisper": ["whispered", "murmured", "breathed", "softly"],
        "shout": ["shouted", "yelled", "screamed", "bellowed", "roared"],
        "trembling": ["trembled", "shaking", "quivered", "stuttered"],
        "sarcastic": ["sarcastically", "rolled her eyes", "sneered", "mocked"],
    }

    for style, keywords in style_keywords.items():
        if any(kw in text for kw in keywords):
            defaults["speaking_style"] = style
            break

    # Preserve existing gender
    if segment.get("speaker_gender") and segment["speaker_gender"] != "unknown":
        defaults["speaker_gender"] = segment["speaker_gender"]

    return {**segment, **defaults}


def get_defaults() -> dict:
    """Return default analysis values."""
    return {
        "speaker_gender": "narrator",
        "emotion": "neutral",
        "emotion_intensity": "medium",
        "scene_mood": "calm",
        "speaking_style": "normal"
    }


def analyze_all_segments(paragraphs: list[dict], model: str = DEFAULT_MODEL) -> list[dict]:
    """
    Analyze all segments across all paragraphs.
    
    Args:
        paragraphs: List of paragraph dicts with 'segments' field
        model: Ollama model name
        
    Returns:
        Paragraphs with enriched segments
    """
    total_segments = sum(len(p.get("segments", [])) for p in paragraphs)
    processed = 0

    for paragraph in paragraphs:
        enriched_segments = []
        for segment in paragraph.get("segments", []):
            enriched = analyze_segment(segment, model)
            enriched_segments.append(enriched)
            processed += 1

            if processed % 10 == 0:
                print(f"  Analyzed {processed}/{total_segments} segments...")

        paragraph["segments"] = enriched_segments

    print(f"  ✓ Analyzed all {total_segments} segments")
    return paragraphs


def check_ollama_status(model: str = DEFAULT_MODEL) -> bool:
    """
    Check if Ollama is running and the model is available.
    
    Returns:
        True if Ollama is ready, False otherwise
    """
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = [m["name"] for m in response.json().get("models", [])]
            # Check if any model name starts with the requested model
            if any(model in m for m in models):
                return True
            else:
                print(f"Model '{model}' not found. Available: {models}")
                print(f"Run: ollama pull {model}")
                return False
    except requests.exceptions.RequestException:
        print("Ollama is not running. Start it with: ollama serve")
        return False
