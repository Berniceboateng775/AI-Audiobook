"""
LLM Analyzer Module
Uses Groq (free cloud LLM API) to analyze text for:
- Character/speaker identification
- Emotion detection
- Scene mood classification

Get your FREE API key at: https://console.groq.com/keys
"""

import os
import json
import re
from groq import Groq

# Groq API setup — set your key as environment variable or paste it below
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
DEFAULT_MODEL = "llama-3.3-70b-versatile"  # Free, fast, excellent quality


def get_client() -> Groq:
    """Get Groq client with API key."""
    if not GROQ_API_KEY:
        raise ValueError(
            "GROQ_API_KEY not set!\n"
            "Get your FREE key at: https://console.groq.com/keys\n"
            "Then set it: set GROQ_API_KEY=your_key_here"
        )
    return Groq(api_key=GROQ_API_KEY)


def analyze_segment(segment: dict, model: str = DEFAULT_MODEL) -> dict:
    """
    Use Groq LLM to analyze a text segment for emotion, speaker, and scene mood.
    
    Args:
        segment: Dict with 'type' and 'text' keys
        model: Groq model name
        
    Returns:
        Enriched segment dict with emotion, speaker_gender, and scene_mood
    """
    text = segment["text"]
    segment_type = segment.get("type", "narration")

    prompt = f"""Analyze this story text segment and return ONLY valid JSON.

Text: "{text}"
Type: {segment_type}

Return this exact JSON structure (no other text, no markdown):
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
- Be specific about speaking_style based on the text"""

    try:
        client = get_client()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a story text analyzer. Return ONLY valid JSON, no other text."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,
            max_tokens=200
        )

        result_text = response.choices[0].message.content
        analysis = parse_llm_response(result_text)

        # Merge LLM analysis with existing segment data
        enriched = {**segment, **analysis}

        # Preserve rule-based gender detection if LLM says "narrator" for dialogue
        if segment_type == "dialogue" and segment.get("speaker_gender") != "unknown":
            enriched["speaker_gender"] = segment["speaker_gender"]

        return enriched

    except Exception as e:
        print(f"  LLM analysis failed: {e}")
        return apply_fallback_analysis(segment)


def parse_llm_response(response_text: str) -> dict:
    """
    Parse JSON from LLM response, handling common formatting issues.
    """
    text = response_text.strip()

    # Try direct JSON parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to extract JSON from markdown code block or raw braces
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

    return get_defaults()


def apply_fallback_analysis(segment: dict) -> dict:
    """
    Apply simple rule-based analysis when LLM is unavailable.
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
    Analyze all segments across all paragraphs using Groq.
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


def check_groq_status() -> bool:
    """
    Check if Groq API key is set and working.
    
    Returns:
        True if Groq is ready, False otherwise
    """
    if not GROQ_API_KEY:
        print("GROQ_API_KEY not set!")
        print("Get your FREE key at: https://console.groq.com/keys")
        print("Then run: set GROQ_API_KEY=your_key_here")
        return False

    try:
        client = get_client()
        # Quick test with a tiny request
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": "Say 'ok'"}],
            max_tokens=5
        )
        return True
    except Exception as e:
        print(f"Groq API error: {e}")
        return False
