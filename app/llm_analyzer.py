"""
LLM Analyzer Module — Powered by Ollama (Mistral)
Smart hybrid approach:
1. PRE-ANALYSIS: Send book excerpt to Ollama to discover ALL characters upfront
2. Rule-based analysis handles MOST segments (instant, free, no API)
3. Ollama LLM used for remaining ambiguous dialogue

Detects individual CHARACTER NAMES so each character gets a unique voice.
"""

import os
import json
import re
import time
import requests

# Ollama setup (local)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")
OLLAMA_TIMEOUT = 120  # seconds — CPU-only Mistral needs more time

# Character registry — tracks all discovered characters across the book
# Maps character name → {"gender": "male"/"female", "voice_id": int}
_character_registry: dict[str, dict] = {}
_male_count = 0
_female_count = 0

# Book context discovered during pre-analysis
_book_context: dict = {}

# ══════════════════════════════════════════════════════════
# NAMES THAT ARE NOT CHARACTERS (false positive blocklist)
# ══════════════════════════════════════════════════════════
_NOT_NAMES = {
    # Adverbs/adjectives that look capitalized in attribution
    "casually", "suddenly", "slowly", "quickly", "quietly", "loudly",
    "softly", "gently", "angrily", "sadly", "happily", "nervously",
    "anxiously", "finally", "desperately", "carefully", "roughly",
    "briefly", "firmly", "sharply", "bitterly", "sweetly", "warmly",
    "coldly", "calmly", "eagerly", "reluctantly", "stubbornly",
    "absently", "dreamily", "wearily", "tiredly", "playfully",
    "sarcastically", "drily", "dryly", "irritably", "impatiently",
    # Not names
    "the", "that", "this", "then", "there", "they", "their", "them",
    "what", "when", "where", "which", "while", "who", "whom", "whose",
    "with", "without", "would", "could", "should", "might", "maybe",
    # Common non-name nouns that get capitalized at sentence start
    "someone", "something", "everyone", "everything", "anyone",
    "anything", "nobody", "nothing", "people", "person",
    # Titles without names
    "the concierge", "the doctor", "the man", "the woman", "the girl",
    "the boy", "the king", "the queen", "the prince", "the princess",
    "the stranger", "the waiter", "the waitress", "the guard",
    "the butler", "the maid", "the driver", "the captain",
}


def _is_valid_name(name: str) -> bool:
    """Check if a detected name is actually a character name."""
    if not name or len(name) < 2:
        return False
    if name.lower() in _NOT_NAMES:
        return False
    # Must start with a letter
    if not name[0].isalpha():
        return False
    # Filter out single common words
    if len(name.split()) == 1 and name.lower().endswith("ly"):
        return False  # Adverbs
    return True


def reset_character_registry():
    """Reset character tracking (call before each new book)."""
    global _character_registry, _male_count, _female_count, _book_context
    _character_registry = {}
    _male_count = 0
    _female_count = 0
    _book_context = {}


def get_character_registry() -> dict:
    """Get the current character registry."""
    return _character_registry.copy()


def register_character(name: str, gender: str) -> dict:
    """
    Register a character and assign a unique voice ID.
    Returns the character's voice info.
    """
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
        # Try to infer from book context
        if name in _book_context.get("characters", {}):
            gender = _book_context["characters"][name].get("gender", "male")
        else:
            gender = "male"  # default

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
# BOOK PRE-ANALYSIS — Send excerpt to Ollama to find characters
# ══════════════════════════════════════════════════════════

def pre_analyze_book(full_text: str, progress_callback=None) -> dict:
    """
    Send the first portion of the book to Ollama to identify:
    - All character names and genders
    - The overall setting/mood
    - Key themes

    This runs BEFORE segment-by-segment analysis so we know
    who all the characters are upfront.
    """
    global _book_context

    if progress_callback:
        progress_callback("🔍 Pre-analyzing book to discover characters...")

    # Take first ~3000 chars (enough to establish characters)
    excerpt = full_text[:3000]

    prompt = f"""Read this excerpt from a novel and identify ALL characters mentioned.

EXCERPT:
{excerpt}

Return ONLY a JSON object with this exact format:
{{
  "characters": [
    {{"name": "FirstName", "gender": "male or female", "role": "brief description"}},
    {{"name": "FirstName", "gender": "male or female", "role": "brief description"}}
  ],
  "setting": "brief description of where/when the story takes place",
  "mood": "one of: calm, romantic, dramatic, suspense, humorous, action"
}}

Rules:
- List EVERY character mentioned, even minor ones
- Use their FIRST NAME only (e.g. "Dante" not "Dante Russo")
- Determine gender from context clues (pronouns, descriptions)
- Include the narrator as a character ONLY if they are a named character
- Return ONLY valid JSON, no other text"""

    system = "You are a literary analysis assistant. Return ONLY valid JSON. Never include explanations."

    result = _ollama_generate(prompt, system)
    if not result:
        print("  Pre-analysis: Ollama unavailable, will discover characters from text")
        return {}

    # Parse the response
    try:
        data = json.loads(result.strip())
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', result, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                print("  Pre-analysis: Could not parse Ollama response")
                return {}
        else:
            print("  Pre-analysis: Could not parse Ollama response")
            return {}

    # Register all discovered characters
    characters = data.get("characters", [])
    _book_context = {
        "characters": {},
        "setting": data.get("setting", ""),
        "mood": data.get("mood", "calm"),
    }

    for char in characters:
        name = char.get("name", "").strip().title()
        gender = char.get("gender", "unknown").lower()
        role = char.get("role", "")

        if name and _is_valid_name(name) and name not in ("Narrator", "Unknown"):
            _book_context["characters"][name] = {"gender": gender, "role": role}
            register_character(name, gender)

    if progress_callback and _character_registry:
        names = [f"{n} ({v['gender']})" for n, v in _character_registry.items()]
        progress_callback(f"🔍 Found {len(_character_registry)} characters: {', '.join(names)}")

    print(f"  Pre-analysis: Setting = {data.get('setting', 'unknown')}")
    print(f"  Pre-analysis: Mood = {data.get('mood', 'unknown')}")
    print(f"  Pre-analysis: {len(_character_registry)} characters discovered")

    return _book_context


# ══════════════════════════════════════════════════════════
# RULE-BASED ANALYSIS (PRIMARY — handles 90%+ of segments)
# ══════════════════════════════════════════════════════════

def apply_rule_based_analysis(segment: dict) -> dict:
    """
    Comprehensive rule-based analysis — no API needed.
    Handles emotion, speaking style, scene mood, and gender detection.
    Also tries to extract character names from attribution tags.
    """
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

    # ── CHARACTER NAME EXTRACTION FROM ATTRIBUTION ────────
    # Match patterns like: "said John", "Mary whispered", "cried Elizabeth"
    attribution = segment.get("attribution", "")
    if attribution:
        name = _extract_name_from_attribution(attribution)
        if name:
            result["speaker_name"] = name

    # ── MATCH AGAINST KNOWN CHARACTERS ───────────────────
    # If no name from attribution, check if context mentions a known character
    if not result["speaker_name"] and segment.get("type") == "dialogue":
        nearby_text = (attribution + " " + original_text).lower()
        for char_name in _character_registry:
            if char_name.lower() in nearby_text:
                result["speaker_name"] = char_name
                break

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

    # ── GENDER (from registry, attribution, or text clues) ──
    if result["speaker_name"] and result["speaker_name"] in _character_registry:
        # Use known gender from registry
        result["speaker_gender"] = _character_registry[result["speaker_name"]]["gender"]
    elif result["speaker_gender"] in ("unknown", "narrator") and segment.get("type") == "dialogue":
        female_cues = ["she", "her ", "herself", "woman", "girl", "lady",
                      "mother", "sister", "daughter", "queen", "princess",
                      "mrs", "miss", "ms"]
        male_cues = ["he ", "him ", "his ", "himself", "man ", "boy",
                    "gentleman", "father", "brother", "son", "king", "prince",
                    "mr ", "sir"]

        attr_text = (attribution + " " + text).lower()
        female_score = sum(1 for w in female_cues if w in attr_text)
        male_score = sum(1 for w in male_cues if w in attr_text)

        if female_score > male_score:
            result["speaker_gender"] = "female"
        elif male_score > female_score:
            result["speaker_gender"] = "male"

    # For narration type, always set to narrator
    if segment.get("type") == "narration":
        result["speaker_gender"] = "narrator"
        result["speaker_name"] = "Narrator"

    # Register the character if we found a valid name
    if result["speaker_name"] and result["speaker_name"] not in ("Narrator", "Unknown", ""):
        char_info = register_character(result["speaker_name"], result["speaker_gender"])
        result["speaker_gender"] = char_info["gender"]
        result["character_voice_id"] = char_info["voice_id"]
    else:
        result["character_voice_id"] = 0

    return {**segment, **result}


def _extract_name_from_attribution(attribution: str) -> str:
    """Extract character name from attribution string, filtering false positives."""
    speech_verbs = (
        r'said|asked|replied|whispered|shouted|yelled|murmured|cried|'
        r'exclaimed|snapped|growled|snarled|laughed|screamed|demanded|'
        r'pleaded|begged|called|answered|continued|added|muttered|'
        r'breathed|sighed|groaned|hissed|roared|bellowed'
    )

    # Pattern: "verb Name"
    name_match = re.search(
        rf'(?:{speech_verbs})\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
        attribution, re.IGNORECASE
    )
    if not name_match:
        # Pattern: "Name verb"
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
# OLLAMA LLM ANALYSIS (for ambiguous segments)
# ══════════════════════════════════════════════════════════

def _ollama_generate(prompt: str, system: str = "") -> str:
    """Call Ollama's generate API with generous timeout for CPU."""
    try:
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 500,
            }
        }
        if system:
            payload["system"] = system

        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            timeout=OLLAMA_TIMEOUT
        )
        resp.raise_for_status()
        return resp.json().get("response", "")
    except requests.exceptions.Timeout:
        print(f"  Ollama timeout ({OLLAMA_TIMEOUT}s) — segment batch skipped")
        return ""
    except Exception as e:
        print(f"  Ollama error: {e}")
        return ""


def analyze_with_llm(segments: list[dict], book_context: str = "") -> list[dict]:
    """
    Use Ollama (Mistral) for a batch of ambiguous segments.
    Focuses on identifying CHARACTER NAMES and gender.
    """
    if not segments:
        return []

    segment_texts = []
    for i, seg in enumerate(segments):
        attr = seg.get("attribution", "")
        text_preview = seg["text"][:200]
        if attr:
            segment_texts.append(f'{i}. Attribution: "{attr}" | Dialogue: "{text_preview}"')
        else:
            segment_texts.append(f'{i}. "{text_preview}"')

    batch_text = "\n".join(segment_texts)

    # Include known characters for context
    known = []
    for name, info in _character_registry.items():
        known.append(f"{name} ({info['gender']})")
    known_str = f"\nKnown characters: {', '.join(known)}" if known else ""

    prompt = f"""Analyze these {len(segments)} dialogue segments from a novel.
For each, identify the CHARACTER NAME of who is speaking, their gender, and the emotion.
{known_str}

{batch_text}

Return ONLY a JSON array with exactly {len(segments)} objects:
[{{"speaker_name":"CharacterName","speaker_gender":"male/female","emotion":"neutral/anger/sadness/love/fear/excitement/humor/suspense","speaking_style":"normal/whisper/shout/trembling/sarcastic/seductive/cold","scene_mood":"calm/romantic/dramatic/suspense/humorous/action"}}]

Rules:
- Use the character's actual FIRST NAME (e.g. "Dante", "Vivian"), not generic labels
- If you can't determine the name, use "Unknown"
- Use the known character list above to match speakers
- Infer gender from the name and context clues
- Return ONLY valid JSON, no other text"""

    system = "You are a literary analysis assistant. Return ONLY valid JSON arrays. Never include explanations."

    result_text = _ollama_generate(prompt, system)
    if not result_text:
        return [apply_rule_based_analysis(s) for s in segments]

    analyses = parse_batch_response(result_text, len(segments))

    enriched = []
    for seg, analysis in zip(segments, analyses):
        merged = {**seg, **analysis}

        if "scene_mood" not in merged:
            merged["scene_mood"] = "calm"
        if "emotion_intensity" not in merged:
            merged["emotion_intensity"] = "medium"

        # Register discovered character
        name = merged.get("speaker_name", "")
        gender = merged.get("speaker_gender", "unknown")
        if name and name not in ("Unknown", "Narrator", "None", "unknown") and _is_valid_name(name):
            char_info = register_character(name, gender)
            merged["speaker_gender"] = char_info["gender"]
            merged["character_voice_id"] = char_info["voice_id"]
        else:
            merged["character_voice_id"] = 0

        enriched.append(merged)
    return enriched


def parse_batch_response(response_text: str, expected_count: int) -> list[dict]:
    """Parse JSON array from LLM response."""
    text = response_text.strip()

    # Try direct parse
    try:
        result = json.loads(text)
        if isinstance(result, list):
            while len(result) < expected_count:
                result.append(get_defaults())
            return result[:expected_count]
    except json.JSONDecodeError:
        pass

    # Try extracting JSON array from text
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
        "speaker_name": "Unknown",
        "speaker_gender": "narrator",
        "emotion": "neutral",
        "emotion_intensity": "medium",
        "scene_mood": "calm",
        "speaking_style": "normal",
        "character_voice_id": 0,
    }


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
    Smart hybrid analysis:
    1. PRE-ANALYZE book to discover all characters upfront
    2. Apply rule-based analysis to ALL segments (instant)
    3. Send ONLY ambiguous dialogue to Ollama (saves resources)
    """
    global OLLAMA_MODEL
    OLLAMA_MODEL = model

    # Reset character registry for each new book
    reset_character_registry()

    # ── Step 0: Book pre-analysis (discover characters) ──
    if full_text and check_ollama_status():
        pre_analyze_book(full_text, progress_callback)
    elif not full_text:
        # Reconstruct text from paragraphs
        all_text = "\n".join(p.get("text", "") for p in paragraphs)
        if all_text and check_ollama_status():
            pre_analyze_book(all_text, progress_callback)

    total = sum(len(p.get("segments", [])) for p in paragraphs)
    if progress_callback:
        progress_callback(f"🧠 Analyzing {total} segments (rule-based first)...")
    print(f"  Analyzing {total} segments (rule-based first)...")

    # ── Step 1: Rule-based analysis for everything ───────
    ambiguous = []

    for p_idx, paragraph in enumerate(paragraphs):
        for s_idx, segment in enumerate(paragraph.get("segments", [])):
            enriched = apply_rule_based_analysis(segment)
            paragraph["segments"][s_idx] = enriched

            # Track ambiguous dialogues for optional Ollama pass
            if (enriched.get("type") == "dialogue" and
                (enriched.get("speaker_name", "") in ("", "Unknown") or
                 enriched.get("speaker_gender") in ("unknown", "narrator"))):
                ambiguous.append((p_idx, s_idx))

    print(f"  Rule-based: Done! ({total} segments analyzed instantly)")
    print(f"  Characters found (rule-based): {len(_character_registry)}")
    for name, info in _character_registry.items():
        print(f"    • {name} ({info['gender']}, voice #{info['voice_id']})")
    print(f"  Ambiguous dialogues needing LLM: {len(ambiguous)}")

    if progress_callback:
        char_list = ", ".join(f"{n} ({v['gender']})" for n, v in _character_registry.items())
        progress_callback(f"🧠 Characters: {char_list or 'none yet'} | {len(ambiguous)} ambiguous segments")

    # ── Step 2: Use Ollama only for ambiguous segments ───
    if ambiguous and check_ollama_status():
        if progress_callback:
            progress_callback(f"🧠 Sending {len(ambiguous)} ambiguous segments to Ollama...")
        print(f"  Sending {len(ambiguous)} ambiguous segments to Ollama ({OLLAMA_MODEL})...")

        BATCH = 5  # Smaller batches for CPU-only (less timeout risk)
        for i in range(0, len(ambiguous), BATCH):
            batch_indices = ambiguous[i:i + BATCH]
            batch_segments = [
                paragraphs[p_idx]["segments"][s_idx]
                for p_idx, s_idx in batch_indices
            ]

            enriched = analyze_with_llm(batch_segments)

            for (p_idx, s_idx), seg in zip(batch_indices, enriched):
                paragraphs[p_idx]["segments"][s_idx] = seg

            done = min(i + BATCH, len(ambiguous))
            print(f"  Ollama: {done}/{len(ambiguous)} ambiguous segments...")
            if progress_callback:
                progress_callback(f"🧠 Ollama: {done}/{len(ambiguous)} ambiguous segments analyzed...")

    # Final character summary
    print(f"\n  === CHARACTER REGISTRY ({len(_character_registry)} characters) ===")
    for name, info in _character_registry.items():
        print(f"    {name}: {info['gender']} | voice #{info['voice_id']}")
    print(f"  Done analyzing all {total} segments!")

    if progress_callback:
        char_summary = ", ".join(f"{n} ({v['gender']})" for n, v in _character_registry.items())
        progress_callback(f"🧠 Done! {len(_character_registry)} characters: {char_summary}")

    return paragraphs


def check_ollama_status() -> bool:
    """Check if Ollama is running locally."""
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        resp.raise_for_status()
        models = [m["name"] for m in resp.json().get("models", [])]
        model_names = [m.split(":")[0] for m in models]
        if OLLAMA_MODEL.split(":")[0] in model_names:
            print(f"  Ollama: Connected! Model '{OLLAMA_MODEL}' ready.")
            return True
        else:
            print(f"  Ollama: Connected but '{OLLAMA_MODEL}' not found.")
            print(f"  Available models: {models}")
            print(f"  Run: ollama pull {OLLAMA_MODEL}")
            print(f"  Using rule-based analysis only (still works great!)")
            return False
    except Exception as e:
        print(f"  Ollama not running: {e}")
        print(f"  Start it with: ollama serve")
        print(f"  Using rule-based analysis only (still works great!)")
        return False
