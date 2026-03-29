"""
LLM Analyzer Module — Powered by Ollama (Mistral)
Optimized for CPU-only machines: makes ONE single Ollama call to discover
all characters, then uses fast rule-based analysis for everything else.

Flow:
1. ONE Ollama call → identifies all characters + genders + scene mood
2. Rule-based → handles emotions, speaking styles, scene moods (instant)
"""

import os
import json
import re
import requests

# Ollama setup (local)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")

# Character registry — tracks all discovered characters
_character_registry: dict[str, dict] = {}
_male_count = 0
_female_count = 0

# Book context from Ollama
_book_context: dict = {}

# ══════════════════════════════════════════════════════════
# FALSE-POSITIVE NAME BLOCKLIST
# ══════════════════════════════════════════════════════════
_NOT_NAMES = {
    "casually", "suddenly", "slowly", "quickly", "quietly", "loudly",
    "softly", "gently", "angrily", "sadly", "happily", "nervously",
    "anxiously", "finally", "desperately", "carefully", "roughly",
    "briefly", "firmly", "sharply", "bitterly", "sweetly", "warmly",
    "coldly", "calmly", "eagerly", "reluctantly", "stubbornly",
    "absently", "dreamily", "wearily", "tiredly", "playfully",
    "sarcastically", "drily", "dryly", "irritably", "impatiently",
    "the", "that", "this", "then", "there", "they", "their", "them",
    "what", "when", "where", "which", "while", "who", "whom", "whose",
    "someone", "something", "everyone", "everything", "anyone",
    "anything", "nobody", "nothing", "people", "person",
    "the concierge", "the doctor", "the man", "the woman", "the girl",
    "the boy", "the king", "the queen", "the stranger", "the waiter",
}


def _is_valid_name(name: str) -> bool:
    if not name or len(name) < 2:
        return False
    if name.lower() in _NOT_NAMES:
        return False
    if not name[0].isalpha():
        return False
    if len(name.split()) == 1 and name.lower().endswith("ly"):
        return False
    return True


def reset_character_registry():
    global _character_registry, _male_count, _female_count, _book_context
    _character_registry = {}
    _male_count = 0
    _female_count = 0
    _book_context = {}


def get_character_registry() -> dict:
    return _character_registry.copy()


def get_book_context() -> dict:
    return _book_context.copy()


def register_character(name: str, gender: str) -> dict:
    global _male_count, _female_count

    name = name.strip().title()
    if not name or name in ("Narrator", "Unknown", "None"):
        return {"gender": "narrator", "voice_id": 0, "name": "Narrator"}

    if not _is_valid_name(name):
        return {"gender": "narrator", "voice_id": 0, "name": "Narrator"}

    if name in _character_registry:
        return _character_registry[name]

    gender = gender.lower()
    if gender not in ("male", "female"):
        # Check book context
        if name in _book_context.get("characters", {}):
            gender = _book_context["characters"][name].get("gender", "male")
        else:
            gender = "male"

    if gender == "male":
        _male_count += 1
        voice_id = _male_count
    else:
        _female_count += 1
        voice_id = _female_count

    _character_registry[name] = {
        "gender": gender,
        "voice_id": voice_id,
        "name": name
    }
    print(f"    New character: {name} ({gender}, voice #{voice_id})")
    return _character_registry[name]


# ══════════════════════════════════════════════════════════
# ONE OLLAMA CALL — discover characters + scene
# ══════════════════════════════════════════════════════════

def discover_characters_with_ollama(full_text: str, progress_callback=None) -> dict:
    """
    Make ONE single Ollama call with a SHORT prompt to identify characters.
    Uses only the first 1500 chars of the book (enough for character intros).
    """
    global _book_context

    if progress_callback:
        progress_callback("🔍 Asking Ollama to identify characters (1 call)...")

    # Short excerpt — keep it small for fast CPU processing
    excerpt = full_text[:1500]

    # Get available sounds
    try:
        from app.sound_effects import get_available_sounds
        sounds = ", ".join(get_available_sounds())
    except:
        sounds = "soft_piano.mp3, nature_ambient.mp3, suspense_ambient.mp3"

    # VERY short, focused prompt — less tokens = faster response
    prompt = f"""List the characters in this story excerpt. For each, give name and gender.

"{excerpt}"

Sounds available: {sounds}

Return JSON only:
{{"characters":[{{"name":"FirstName","gender":"male/female"}}],"mood":"romantic/dramatic/calm/suspense/action","sounds":{{"romantic":"soft_piano.mp3","tense":"suspense_ambient.mp3"}}}}"""

    try:
        print("  Ollama: Sending character discovery request...")
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "system": "Return ONLY valid JSON. No explanations.",
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 300,  # Short response needed
                }
            },
            timeout=None  # No timeout
        )
        resp.raise_for_status()
        result = resp.json().get("response", "")
    except Exception as e:
        print(f"  Ollama error: {e}")
        if progress_callback:
            progress_callback("🔍 Ollama unavailable — using rule-based analysis only")
        return {}

    # Parse response
    try:
        data = json.loads(result.strip())
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', result, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                print(f"  Could not parse Ollama response: {result[:200]}")
                return {}
        else:
            print(f"  Could not parse Ollama response: {result[:200]}")
            return {}

    # Register characters
    _book_context = {
        "characters": {},
        "mood": data.get("mood", "calm"),
        "scene_sounds": data.get("sounds", data.get("scene_sounds", {})),
    }

    for char in data.get("characters", []):
        name = char.get("name", "").strip().title()
        gender = char.get("gender", "unknown").lower()
        if name and _is_valid_name(name) and name not in ("Narrator", "Unknown"):
            _book_context["characters"][name] = {"gender": gender}
            register_character(name, gender)

    if progress_callback and _character_registry:
        names = [f"{n} ({v['gender']})" for n, v in _character_registry.items()]
        progress_callback(f"🔍 Found {len(_character_registry)} characters: {', '.join(names)}")

    # Log
    print(f"  Ollama: Found {len(_character_registry)} characters")
    print(f"  Mood: {_book_context['mood']}")
    scene_sounds = _book_context.get("scene_sounds", {})
    if scene_sounds:
        print(f"  Scene sounds: {scene_sounds}")
        if progress_callback:
            progress_callback(f"🎵 Sound mapping: {scene_sounds}")

    return _book_context


# ══════════════════════════════════════════════════════════
# RULE-BASED ANALYSIS (handles ALL segments — instant)
# ══════════════════════════════════════════════════════════

def apply_rule_based_analysis(segment: dict) -> dict:
    text = segment["text"].lower()
    original_text = segment.get("text", "")
    result = {
        "speaker_gender": segment.get("speaker_gender", "narrator"),
        "speaker_name": segment.get("speaker_name", ""),
        "emotion": "neutral",
        "emotion_intensity": "medium",
        "scene_mood": _book_context.get("mood", "calm"),
        "speaking_style": "normal"
    }

    # ── Character name from attribution ──
    attribution = segment.get("attribution", "")
    if attribution:
        name = _extract_name_from_attribution(attribution)
        if name:
            result["speaker_name"] = name

    # ── Match known characters in nearby text ──
    if not result["speaker_name"] and segment.get("type") == "dialogue":
        nearby_text = (attribution + " " + original_text).lower()
        for char_name in _character_registry:
            if char_name.lower() in nearby_text:
                result["speaker_name"] = char_name
                break

    # ── Emotion detection ──
    emotion_rules = {
        "anger": {
            "keywords": ["angry", "furious", "rage", "hate", "fury",
                        "shouted", "yelled", "screamed", "slammed", "growled",
                        "clenched", "seething", "snapped", "snarled"],
            "mood": "dramatic", "intensity": "high"
        },
        "sadness": {
            "keywords": ["sad", "cried", "tears", "sobbed", "grief",
                        "wept", "heartbroken", "ached", "pain", "lonely",
                        "hurt", "broken", "miserable", "sorrow"],
            "mood": "dramatic", "intensity": "high"
        },
        "love": {
            "keywords": ["love", "loved", "kiss", "kissed", "embrace",
                        "heart", "darling", "tender", "caress", "passion",
                        "desire", "beautiful", "adore", "gentle", "warm"],
            "mood": "romantic", "intensity": "medium"
        },
        "fear": {
            "keywords": ["afraid", "scared", "terrified", "trembled", "horror",
                        "panic", "shook", "frozen", "dread", "danger"],
            "mood": "suspense", "intensity": "high"
        },
        "excitement": {
            "keywords": ["excited", "thrilled", "jumped", "laughed", "grinned",
                        "amazing", "incredible", "smiled", "delighted", "joy"],
            "mood": "humorous", "intensity": "medium"
        },
        "suspense": {
            "keywords": ["slowly", "crept", "shadow", "silence", "watched",
                        "dark", "darkness", "quiet", "suddenly", "froze", "tense"],
            "mood": "suspense", "intensity": "medium"
        },
        "humor": {
            "keywords": ["laughed", "chuckled", "grinned", "smirked", "funny",
                        "joke", "teased", "playful", "amused", "giggled"],
            "mood": "humorous", "intensity": "low"
        }
    }

    for emotion, rules in emotion_rules.items():
        if any(kw in text for kw in rules["keywords"]):
            result["emotion"] = emotion
            result["scene_mood"] = rules["mood"]
            result["emotion_intensity"] = rules["intensity"]
            break

    # ── Speaking style ──
    style_rules = {
        "whisper": ["whispered", "murmured", "breathed", "softly", "quietly", "hushed"],
        "shout": ["shouted", "yelled", "screamed", "bellowed", "roared", "demanded"],
        "trembling": ["trembled", "shaking", "quivered", "stuttered", "voice cracked"],
        "sarcastic": ["sarcastically", "rolled her eyes", "rolled his eyes", "sneered", "scoffed"],
        "seductive": ["purred", "sultry", "seductively", "husky", "teasing"],
        "cold": ["coldly", "icily", "flatly", "emotionless", "detached"]
    }

    for style, keywords in style_rules.items():
        if any(kw in text for kw in keywords):
            result["speaking_style"] = style
            break

    # ── Gender from registry or text clues ──
    if result["speaker_name"] and result["speaker_name"] in _character_registry:
        result["speaker_gender"] = _character_registry[result["speaker_name"]]["gender"]
    elif result["speaker_gender"] in ("unknown", "narrator") and segment.get("type") == "dialogue":
        female_cues = ["she", "her ", "herself", "woman", "girl", "lady",
                      "mother", "sister", "daughter", "mrs", "miss"]
        male_cues = ["he ", "him ", "his ", "himself", "man ", "boy",
                    "father", "brother", "son", "mr ", "sir"]
        attr_text = (attribution + " " + text).lower()
        f_score = sum(1 for w in female_cues if w in attr_text)
        m_score = sum(1 for w in male_cues if w in attr_text)
        if f_score > m_score:
            result["speaker_gender"] = "female"
        elif m_score > f_score:
            result["speaker_gender"] = "male"

    # Narration → narrator
    if segment.get("type") == "narration":
        result["speaker_gender"] = "narrator"
        result["speaker_name"] = "Narrator"

    # Register character
    if result["speaker_name"] and result["speaker_name"] not in ("Narrator", "Unknown", ""):
        char_info = register_character(result["speaker_name"], result["speaker_gender"])
        result["speaker_gender"] = char_info["gender"]
        result["character_voice_id"] = char_info["voice_id"]
    else:
        result["character_voice_id"] = 0

    return {**segment, **result}


def _extract_name_from_attribution(attribution: str) -> str:
    speech_verbs = (
        r'said|asked|replied|whispered|shouted|yelled|murmured|cried|'
        r'exclaimed|snapped|growled|snarled|laughed|screamed|demanded|'
        r'pleaded|begged|called|answered|continued|added|muttered|'
        r'breathed|sighed|groaned|hissed|roared|bellowed'
    )
    name_match = re.search(
        rf'(?:{speech_verbs})\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
        attribution, re.IGNORECASE
    )
    if not name_match:
        name_match = re.search(
            rf'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:{speech_verbs})',
            attribution
        )
    if name_match:
        name = name_match.group(1).strip()
        if _is_valid_name(name):
            return name
    return ""


# ══════════════════════════════════════════════════════════
# MAIN ANALYSIS FUNCTION
# ══════════════════════════════════════════════════════════

def analyze_all_segments(
    paragraphs: list[dict],
    model: str = OLLAMA_MODEL,
    full_text: str = "",
    progress_callback=None
) -> list[dict]:
    """
    Optimized analysis:
    1. ONE Ollama call → discover characters (takes ~2 min on CPU)
    2. Rule-based → analyze ALL segments (instant)
    No batch segment analysis = no 20+ minute waits.
    """
    global OLLAMA_MODEL
    OLLAMA_MODEL = model

    reset_character_registry()

    # ── Step 1: ONE Ollama call for characters ──
    if full_text:
        discover_characters_with_ollama(full_text, progress_callback)
    else:
        all_text = "\n".join(p.get("text", "") for p in paragraphs)
        if all_text:
            discover_characters_with_ollama(all_text, progress_callback)

    # ── Step 2: Rule-based analysis for ALL segments (instant) ──
    total = sum(len(p.get("segments", [])) for p in paragraphs)
    if progress_callback:
        progress_callback(f"🧠 Analyzing {total} segments (rule-based — instant)...")
    print(f"  Analyzing {total} segments (rule-based)...")

    for paragraph in paragraphs:
        for s_idx, segment in enumerate(paragraph.get("segments", [])):
            paragraph["segments"][s_idx] = apply_rule_based_analysis(segment)

    # Summary
    print(f"  Rule-based: Done! ({total} segments)")
    print(f"\n  === CHARACTER REGISTRY ({len(_character_registry)} characters) ===")
    for name, info in _character_registry.items():
        print(f"    {name}: {info['gender']} | voice #{info['voice_id']}")

    if progress_callback:
        char_summary = ", ".join(f"{n} ({v['gender']})" for n, v in _character_registry.items())
        progress_callback(f"🧠 Done! {len(_character_registry)} characters: {char_summary}")

    return paragraphs


def check_ollama_status() -> bool:
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        resp.raise_for_status()
        models = [m["name"] for m in resp.json().get("models", [])]
        model_names = [m.split(":")[0] for m in models]
        if OLLAMA_MODEL.split(":")[0] in model_names:
            print(f"  Ollama: Connected! Model '{OLLAMA_MODEL}' ready.")
            return True
        else:
            print(f"  Ollama: '{OLLAMA_MODEL}' not found. Available: {models}")
            return False
    except Exception as e:
        print(f"  Ollama not running: {e}")
        return False
