"""
LLM Analyzer Module
Smart hybrid approach:
1. Rule-based analysis handles MOST segments (instant, free, no API)
2. Groq LLM only used for ambiguous dialogue (unknown gender/emotion)

This way a 578-page book uses minimal API tokens.
"""

import os
import json
import re
import time
from groq import Groq

# Groq API setup
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
DEFAULT_MODEL = "llama-3.1-8b-instant"  # Smaller model = fewer tokens used


def get_client() -> Groq:
    """Get Groq client with API key."""
    if not GROQ_API_KEY:
        return None
    return Groq(api_key=GROQ_API_KEY)


# ══════════════════════════════════════════════════════════
# RULE-BASED ANALYSIS (PRIMARY — handles 90%+ of segments)
# ══════════════════════════════════════════════════════════

def apply_rule_based_analysis(segment: dict) -> dict:
    """
    Comprehensive rule-based analysis — no API needed.
    Handles emotion, speaking style, scene mood, and gender detection.
    Works great for fiction/romance novels.
    """
    text = segment["text"].lower()
    result = {
        "speaker_gender": segment.get("speaker_gender", "narrator"),
        "emotion": "neutral",
        "emotion_intensity": "medium",
        "scene_mood": "calm",
        "speaking_style": "normal"
    }

    # ── EMOTION DETECTION ────────────────────────────────
    emotion_rules = {
        "anger": {
            "keywords": ["angry", "furious", "rage", "hate", "hated", "fury",
                        "shouted", "yelled", "screamed", "slammed", "growled",
                        "clenched", "seething", "livid", "snapped", "snarled"],
            "mood": "dramatic",
            "intensity": "high"
        },
        "sadness": {
            "keywords": ["sad", "cried", "tears", "sobbed", "grief", "mourning",
                        "wept", "heartbroken", "ached", "pain", "lonely", "loss",
                        "hurt", "broken", "miserable", "sorrow", "regret"],
            "mood": "dramatic",
            "intensity": "high"
        },
        "love": {
            "keywords": ["love", "loved", "kiss", "kissed", "embrace", "embraced",
                        "heart", "darling", "tender", "caress", "passion",
                        "desire", "beautiful", "gorgeous", "adore", "cherish",
                        "gentle", "softly", "warm", "longing", "yearning"],
            "mood": "romantic",
            "intensity": "medium"
        },
        "fear": {
            "keywords": ["afraid", "scared", "terrified", "trembled", "horror",
                        "panic", "shook", "frozen", "dread", "nightmare",
                        "shiver", "haunted", "danger", "threat", "alarmed"],
            "mood": "suspense",
            "intensity": "high"
        },
        "excitement": {
            "keywords": ["excited", "thrilled", "jumped", "laughed", "grinned",
                        "amazing", "incredible", "wonderful", "smiled", "beamed",
                        "delighted", "joy", "happy", "glow", "sparkle"],
            "mood": "humorous",
            "intensity": "medium"
        },
        "suspense": {
            "keywords": ["slowly", "crept", "shadow", "silence", "watched",
                        "waited", "dark", "darkness", "quiet", "still",
                        "carefully", "suddenly", "froze", "motionless", "tense"],
            "mood": "suspense",
            "intensity": "medium"
        },
        "humor": {
            "keywords": ["laughed", "chuckled", "grinned", "smirked", "funny",
                        "ridiculous", "joke", "teased", "playful", "amused",
                        "giggled", "snorted", "rolled eyes"],
            "mood": "humorous",
            "intensity": "low"
        }
    }

    for emotion, rules in emotion_rules.items():
        if any(kw in text for kw in rules["keywords"]):
            result["emotion"] = emotion
            result["scene_mood"] = rules["mood"]
            result["emotion_intensity"] = rules["intensity"]
            break

    # ── SPEAKING STYLE DETECTION ─────────────────────────
    style_rules = {
        "whisper": ["whispered", "murmured", "breathed", "softly", "quietly",
                    "hushed", "under her breath", "under his breath", "low voice"],
        "shout": ["shouted", "yelled", "screamed", "bellowed", "roared",
                 "demanded", "barked", "thundered", "exclaimed"],
        "trembling": ["trembled", "shaking", "quivered", "stuttered",
                     "voice broke", "voice cracked", "choked", "shakily"],
        "sarcastic": ["sarcastically", "rolled her eyes", "rolled his eyes",
                     "sneered", "mocked", "scoffed", "dryly", "deadpan"],
        "seductive": ["purred", "sultry", "seductively", "husky", "velvety",
                     "sensually", "teasing", "silky"],
        "cold": ["coldly", "icily", "flatly", "emotionless", "detached",
                "monotone", "blank", "stone-faced"]
    }

    for style, keywords in style_rules.items():
        if any(kw in text for kw in keywords):
            result["speaking_style"] = style
            break

    # ── GENDER (preserve existing or detect from text) ───
    if result["speaker_gender"] == "unknown":
        # Try to detect from the text itself
        female_names_common = ["she", "her ", "herself", "woman", "girl", "lady",
                              "mother", "sister", "daughter", "queen", "princess"]
        male_names_common = ["he ", "him ", "his ", "himself", "man ", "boy",
                            "gentleman", "father", "brother", "son", "king", "prince"]

        female_score = sum(1 for w in female_names_common if w in text)
        male_score = sum(1 for w in male_names_common if w in text)

        if female_score > male_score:
            result["speaker_gender"] = "female"
        elif male_score > female_score:
            result["speaker_gender"] = "male"

    # For narration type, always set to narrator
    if segment.get("type") == "narration":
        result["speaker_gender"] = "narrator"

    return {**segment, **result}


# ══════════════════════════════════════════════════════════
# LLM ANALYSIS (OPTIONAL — only for ambiguous segments)
# ══════════════════════════════════════════════════════════

def analyze_with_llm(segments: list[dict], model: str = DEFAULT_MODEL) -> list[dict]:
    """
    Use Groq LLM for a small batch of ambiguous segments.
    Only called for dialogue segments with unknown gender.
    """
    client = get_client()
    if not client or not segments:
        return [apply_rule_based_analysis(s) for s in segments]

    segment_texts = []
    for i, seg in enumerate(segments):
        segment_texts.append(f'{i}. "{seg["text"][:150]}"')

    batch_text = "\n".join(segment_texts)

    prompt = f"""Analyze these {len(segments)} dialogue segments. Return ONLY a JSON array.

{batch_text}

Return JSON array:
[{{"speaker_gender":"male/female","emotion":"neutral/anger/sadness/love/fear/excitement/humor/suspense","speaking_style":"normal/whisper/shout/trembling/sarcastic/seductive/cold"}}]"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Return ONLY valid JSON arrays."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=800
        )

        result_text = response.choices[0].message.content
        analyses = parse_batch_response(result_text, len(segments))

        enriched = []
        for seg, analysis in zip(segments, analyses):
            merged = {**seg, **analysis}
            if "scene_mood" not in merged:
                merged["scene_mood"] = "calm"
            if "emotion_intensity" not in merged:
                merged["emotion_intensity"] = "medium"
            enriched.append(merged)
        return enriched

    except Exception as e:
        print(f"  LLM failed (using rules): {e}")
        return [apply_rule_based_analysis(s) for s in segments]


def parse_batch_response(response_text: str, expected_count: int) -> list[dict]:
    """Parse JSON array from LLM response."""
    text = response_text.strip()

    for attempt in [text]:
        try:
            result = json.loads(attempt)
            if isinstance(result, list):
                while len(result) < expected_count:
                    result.append(get_defaults())
                return result[:expected_count]
        except json.JSONDecodeError:
            pass

    # Try extracting from code blocks
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group())
            if isinstance(result, list):
                while len(result) < expected_count:
                    result.append(get_defaults())
                return result[:expected_count]
        except json.JSONDecodeError:
            pass

    return [get_defaults() for _ in range(expected_count)]


def get_defaults() -> dict:
    return {
        "speaker_gender": "narrator",
        "emotion": "neutral",
        "emotion_intensity": "medium",
        "scene_mood": "calm",
        "speaking_style": "normal"
    }


# ══════════════════════════════════════════════════════════
# MAIN ANALYSIS FUNCTION
# ══════════════════════════════════════════════════════════

def analyze_all_segments(paragraphs: list[dict], model: str = DEFAULT_MODEL) -> list[dict]:
    """
    Smart hybrid analysis:
    1. Apply rule-based analysis to ALL segments (instant)
    2. Send ONLY ambiguous dialogue to Groq (saves tokens)
    """
    total = sum(len(p.get("segments", [])) for p in paragraphs)
    print(f"  Analyzing {total} segments (rule-based first)...")

    # Step 1: Rule-based analysis for everything
    ambiguous = []  # (paragraph_idx, segment_idx) for unknown gender dialogues
    
    for p_idx, paragraph in enumerate(paragraphs):
        for s_idx, segment in enumerate(paragraph.get("segments", [])):
            enriched = apply_rule_based_analysis(segment)
            paragraph["segments"][s_idx] = enriched

            # Track ambiguous dialogues for optional LLM pass
            if (enriched.get("type") == "dialogue" and 
                enriched.get("speaker_gender") in ("unknown", "narrator")):
                ambiguous.append((p_idx, s_idx))

    print(f"  Rule-based: Done! ({total} segments analyzed instantly)")
    print(f"  Ambiguous dialogues needing LLM: {len(ambiguous)}")

    # Step 2: Use Groq only for ambiguous segments (if available)
    if ambiguous and GROQ_API_KEY:
        print(f"  Sending {len(ambiguous)} ambiguous segments to Groq...")
        
        BATCH = 20
        for i in range(0, len(ambiguous), BATCH):
            batch_indices = ambiguous[i:i + BATCH]
            batch_segments = [
                paragraphs[p_idx]["segments"][s_idx] 
                for p_idx, s_idx in batch_indices
            ]

            enriched = analyze_with_llm(batch_segments, model)

            for (p_idx, s_idx), seg in zip(batch_indices, enriched):
                paragraphs[p_idx]["segments"][s_idx] = seg

            done = min(i + BATCH, len(ambiguous))
            print(f"  LLM: {done}/{len(ambiguous)} ambiguous segments...")

            # Small delay to avoid rate limits
            if i + BATCH < len(ambiguous):
                time.sleep(1)

    print(f"  Done analyzing all {total} segments!")
    return paragraphs


def check_groq_status() -> bool:
    """Check if Groq API is available."""
    if not GROQ_API_KEY:
        print("  No GROQ_API_KEY set — using rule-based analysis only (still works great!)")
        return True  # We can still work with rule-based only

    try:
        client = get_client()
        client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": "ok"}],
            max_tokens=5
        )
        print("  Groq API: Connected!")
        return True
    except Exception as e:
        print(f"  Groq API unavailable: {e}")
        print("  Falling back to rule-based analysis (still works great!)")
        return True  # Don't block — rule-based is fine
