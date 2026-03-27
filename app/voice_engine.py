"""
Voice Engine Module — Powered by Chatterbox TTS (Resemble AI)
Uses HuggingFace Inference API with robust retry/queue handling.

Features:
- Voice cloning from reference clips via Chatterbox
- Each CHARACTER gets a unique voice profile (exaggeration, temperature, cfg)
- Smart retry with exponential backoff when queue is full
- Fallback chain: Chatterbox → pyttsx3 (local) → gTTS (Google)
- POV-aware narrator gender
"""

import os
import shutil
import tempfile
import time
import pyttsx3
from pydub import AudioSegment
from gradio_client import Client, handle_file


# ══════════════════════════════════════════════════════════
# AUTO-DETECT FFMPEG
# ══════════════════════════════════════════════════════════

def _find_ffmpeg():
    if shutil.which("ffmpeg"):
        return
    search_paths = [
        os.path.expanduser(r"~\AppData\Local\Microsoft\WinGet\Links"),
        r"C:\ffmpeg\bin",
        r"C:\ProgramData\chocolatey\bin",
    ]
    for d in search_paths:
        if os.path.exists(os.path.join(d, "ffmpeg.exe")):
            os.environ["PATH"] = d + ";" + os.environ.get("PATH", "")
            AudioSegment.converter = os.path.join(d, "ffmpeg.exe")
            if os.path.exists(os.path.join(d, "ffprobe.exe")):
                AudioSegment.ffprobe = os.path.join(d, "ffprobe.exe")
            print(f"  Found ffmpeg at: {d}")
            return
    wp = os.path.expanduser(r"~\AppData\Local\Microsoft\WinGet\Packages")
    if os.path.exists(wp):
        for root, dirs, files in os.walk(wp):
            if "ffmpeg.exe" in files:
                os.environ["PATH"] = root + ";" + os.environ.get("PATH", "")
                AudioSegment.converter = os.path.join(root, "ffmpeg.exe")
                if "ffprobe.exe" in files:
                    AudioSegment.ffprobe = os.path.join(root, "ffprobe.exe")
                print(f"  Found ffmpeg at: {root}")
                return

_find_ffmpeg()


# ══════════════════════════════════════════════════════════
# VOICE REFERENCE CLIPS
# ══════════════════════════════════════════════════════════

VOICES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "voices")

# Default reference audio
_DEFAULT_REF = "https://github.com/gradio-app/gradio/raw/main/test/test_files/audio_sample.wav"


def _get_voice_ref(voice_name: str):
    """Get voice reference — checks local files first, then uses default."""
    if os.path.exists(VOICES_DIR):
        for ext in [".wav", ".mp3", ".flac"]:
            path = os.path.join(VOICES_DIR, f"{voice_name}{ext}")
            if os.path.exists(path):
                return handle_file(path)
    return handle_file(_DEFAULT_REF)


# ══════════════════════════════════════════════════════════
# CHATTERBOX API CLIENT — with retry logic
# ══════════════════════════════════════════════════════════

_client = None
_client_failed = False
_consecutive_failures = 0
_MAX_CONSECUTIVE_FAILURES = 10  # After this many, switch to fallback for a while
_last_failure_time = 0
_COOLDOWN_SECONDS = 120  # Wait 2 min before retrying after too many failures


def _get_client():
    """Get or create the Chatterbox Gradio client with smart reconnection."""
    global _client, _client_failed, _consecutive_failures, _last_failure_time

    # If we've had too many failures, wait for cooldown
    if _client_failed and _consecutive_failures >= _MAX_CONSECUTIVE_FAILURES:
        elapsed = time.time() - _last_failure_time
        if elapsed < _COOLDOWN_SECONDS:
            return None
        else:
            # Cooldown expired, try again
            print(f"  Chatterbox: Cooldown expired, retrying connection...")
            _client_failed = False
            _client = None
            _consecutive_failures = 0

    if _client is not None:
        return _client

    try:
        _client = Client("ResembleAI/Chatterbox")
        print("  Chatterbox TTS: Connected to HuggingFace!")
        _consecutive_failures = 0
        return _client
    except Exception as e:
        print(f"  Chatterbox connection failed: {e}")
        _client_failed = True
        _last_failure_time = time.time()
        return None


# ══════════════════════════════════════════════════════════
# PER-CHARACTER VOICE PROFILES
# Each character gets unique Chatterbox settings so they sound different!
# We vary: exaggeration (expressiveness), temperature (variation),
# and cfg (guidance) to make each character's voice distinct.
# ══════════════════════════════════════════════════════════

# 20 unique voice profiles — applied per character_voice_id
_CHARACTER_PROFILES = [
    # (exaggeration, temperature, cfg_weight)  — voice #0 = narrator
    (0.40, 0.70, 0.50),   # 0: Narrator — balanced, neutral
    (0.35, 0.65, 0.55),   # 1: Calm, steady
    (0.50, 0.75, 0.45),   # 2: Expressive, warm
    (0.30, 0.60, 0.60),   # 3: Reserved, precise
    (0.60, 0.80, 0.40),   # 4: Animated, lively
    (0.25, 0.55, 0.65),   # 5: Quiet, measured
    (0.55, 0.85, 0.35),   # 6: Bold, dramatic
    (0.45, 0.70, 0.50),   # 7: Smooth, natural
    (0.65, 0.75, 0.45),   # 8: Energetic, bright
    (0.20, 0.50, 0.70),   # 9: Soft-spoken, gentle
    (0.70, 0.90, 0.30),   # 10: Very expressive, theatrical
    (0.38, 0.68, 0.52),   # 11: Slightly warm
    (0.52, 0.72, 0.48),   # 12: Slightly bold
    (0.28, 0.58, 0.62),   # 13: Understated
    (0.58, 0.82, 0.38),   # 14: Vivid
    (0.42, 0.62, 0.55),   # 15: Controlled
    (0.48, 0.78, 0.42),   # 16: Free-flowing
    (0.32, 0.66, 0.58),   # 17: Composed
    (0.62, 0.88, 0.32),   # 18: Passionate
    (0.22, 0.52, 0.68),   # 19: Subdued
]


def _get_character_settings(voice_id: int, emotion: str) -> dict:
    """
    Get Chatterbox TTS settings for a specific character + emotion.
    Each character has a unique base profile, then emotion modifies it.
    """
    # Get base profile for this character
    idx = voice_id % len(_CHARACTER_PROFILES)
    base_exag, base_temp, base_cfg = _CHARACTER_PROFILES[idx]

    # Emotion modifiers (added on top of character base)
    emotion_mods = {
        "neutral":    (0.0,  0.0,  0.0),
        "anger":      (+0.25, +0.15, -0.15),
        "sadness":    (+0.10, -0.10, -0.05),
        "love":       (+0.10, -0.05, +0.05),
        "fear":       (+0.20, +0.10, -0.15),
        "excitement": (+0.20, +0.15, -0.10),
        "humor":      (+0.15, +0.10, +0.00),
        "suspense":   (+0.05, +0.05, -0.15),
    }

    mod = emotion_mods.get(emotion, (0.0, 0.0, 0.0))

    return {
        "exaggeration": max(0.0, min(1.0, base_exag + mod[0])),
        "temperature":  max(0.1, min(1.0, base_temp + mod[1])),
        "cfg":          max(0.1, min(1.0, base_cfg  + mod[2])),
    }


# ══════════════════════════════════════════════════════════
# VOICE NAME SELECTION
# ══════════════════════════════════════════════════════════

STYLE_VOLUME_DB = {
    "normal": 0, "whisper": -8, "shout": +5, "trembling": -4,
    "sarcastic": 0, "seductive": -5, "cold": -2,
}


def get_voice_name(segment: dict) -> str:
    """
    Map segment to a voice reference name.
    Each character type gets a unique voice reference clip.
    """
    gender = segment.get("speaker_gender", "narrator")
    seg_type = segment.get("type", "narration")
    style = segment.get("speaking_style", "normal")

    # NARRATION — use POV narrator voice
    if seg_type == "narration" or gender == "narrator":
        pov = segment.get("pov_gender", "male")
        return f"narrator_{pov}"

    # DIALOGUE
    if gender == "female":
        if style in ["whisper", "seductive", "trembling"]:
            return "female_soft"
        elif style in ["shout", "cold"]:
            return "female_strong"
        return "female_lead"

    if gender == "male":
        if style in ["shout", "cold"]:
            return "male_strong"
        return "male_lead"

    pov = segment.get("pov_gender", "male")
    return f"narrator_{pov}"


# ══════════════════════════════════════════════════════════
# TTS GENERATION — Chatterbox with retry
# ══════════════════════════════════════════════════════════

_RETRY_DELAYS = [5, 10, 20, 30]  # Seconds to wait between retries


def generate_speech_chatterbox(text: str, voice_name: str,
                                emotion: str = "neutral",
                                voice_id: int = 0) -> AudioSegment:
    """Generate speech using Chatterbox TTS with retry on queue full."""
    global _consecutive_failures, _last_failure_time

    text = text.strip()
    if len(text) < 2:
        return AudioSegment.silent(duration=300)

    client = _get_client()
    if client is None:
        return _generate_fallback(text)

    # Get per-character settings
    settings = _get_character_settings(voice_id, emotion)
    voice_ref = _get_voice_ref(voice_name)

    # Try with retries
    for attempt in range(len(_RETRY_DELAYS) + 1):
        try:
            result = client.predict(
                text_input=text,
                audio_prompt_path_input=voice_ref,
                exaggeration_input=settings["exaggeration"],
                temperature_input=settings["temperature"],
                cfgw_input=settings["cfg"],
                api_name="/generate_tts_audio"
            )

            if not result or not os.path.exists(result):
                print(f"  Chatterbox: no output for '{text[:30]}...'")
                return _generate_fallback(text)

            audio = AudioSegment.from_wav(result)
            _consecutive_failures = 0  # Reset on success
            return audio

        except Exception as e:
            error_msg = str(e).lower()
            is_queue_error = ("queue" in error_msg or "exceeded" in error_msg
                              or "503" in error_msg or "too many" in error_msg)

            if is_queue_error and attempt < len(_RETRY_DELAYS):
                delay = _RETRY_DELAYS[attempt]
                print(f"  Chatterbox queue full — waiting {delay}s before retry "
                      f"({attempt + 1}/{len(_RETRY_DELAYS)})...")
                time.sleep(delay)
                # Reconnect client in case the Space restarted
                if attempt >= 2:
                    global _client
                    _client = None
                    client = _get_client()
                    if client is None:
                        break
                continue
            else:
                _consecutive_failures += 1
                _last_failure_time = time.time()
                if is_queue_error:
                    print(f"  Chatterbox queue full after {attempt + 1} attempts, "
                          f"using fallback (failures: {_consecutive_failures}/"
                          f"{_MAX_CONSECUTIVE_FAILURES})")
                else:
                    print(f"  Chatterbox error: {str(e)[:80]}")
                return _generate_fallback(text)

    return _generate_fallback(text)


def _generate_fallback(text: str) -> AudioSegment:
    """Fallback chain: pyttsx3 (local) → gTTS (Google) → silence."""
    # Try pyttsx3 first (local, no internet needed)
    try:
        audio = _generate_speech_pyttsx3(text)
        if audio and len(audio) > 100:
            return audio
    except Exception:
        pass

    # Then gTTS
    try:
        return _generate_speech_gtts(text)
    except Exception as e:
        print(f"  All TTS fallbacks failed: {e}")
        return AudioSegment.silent(duration=500)


def _generate_speech_pyttsx3(text: str) -> AudioSegment:
    """Local fallback using Windows SAPI voices."""
    try:
        engine = pyttsx3.init()
        engine.setProperty("rate", 165)
        engine.setProperty("volume", 0.9)
        temp_file = tempfile.mktemp(suffix=".wav")
        engine.save_to_file(text, temp_file)
        engine.runAndWait()
        engine.stop()

        if not os.path.exists(temp_file) or os.path.getsize(temp_file) < 100:
            return _generate_speech_gtts(text)

        audio = AudioSegment.from_wav(temp_file)
        try:
            os.remove(temp_file)
        except OSError:
            pass
        return audio
    except Exception as e:
        print(f"  pyttsx3 fallback error: {e}")
        return _generate_speech_gtts(text)


def _generate_speech_gtts(text: str) -> AudioSegment:
    """Last resort: Google TTS."""
    try:
        from gtts import gTTS
        temp_file = tempfile.mktemp(suffix=".mp3")
        tts = gTTS(text, lang='en')
        tts.save(temp_file)
        audio = AudioSegment.from_mp3(temp_file)
        os.remove(temp_file)
        return audio
    except Exception as e:
        print(f"  gTTS fallback error: {e}")
        return AudioSegment.silent(duration=500)


# ══════════════════════════════════════════════════════════
# PUBLIC API — used by audio_assembler
# ══════════════════════════════════════════════════════════

def generate_speech(text, voice=None, emotion="neutral", speaking_style="normal"):
    """Generate speech — used by audio_assembler for headings."""
    text = text.strip()
    if len(text) < 2:
        return AudioSegment.silent(duration=300)

    audio = generate_speech_chatterbox(text, "narrator_female", emotion, voice_id=0)

    vol = STYLE_VOLUME_DB.get(speaking_style, 0)
    if vol != 0:
        audio = audio + vol
    if speaking_style == "whisper":
        audio = audio.low_pass_filter(3000)

    return audio


def generate_segment_audio(segment: dict) -> AudioSegment:
    """Generate audio for a fully analyzed segment with character-specific voice."""
    text = segment.get("text", "").strip()
    if not text or len(text) < 2:
        return AudioSegment.silent(duration=200)

    voice_name = get_voice_name(segment)
    emotion = segment.get("emotion", "neutral")
    style = segment.get("speaking_style", "normal")
    voice_id = segment.get("character_voice_id", 0)

    audio = generate_speech_chatterbox(text, voice_name, emotion, voice_id)

    vol = STYLE_VOLUME_DB.get(style, 0)
    if vol != 0:
        audio = audio + vol
    if style == "whisper":
        audio = audio.low_pass_filter(3000)

    return audio


# ══════════════════════════════════════════════════════════
# POV DETECTION
# ══════════════════════════════════════════════════════════

def detect_paragraph_pov(paragraph: dict) -> str:
    """Detect narrator POV gender per paragraph."""
    segments = paragraph.get("segments", [])
    full_text = paragraph.get("text", "").lower()

    female_pov_cues = [
        "his eyes", "his jaw", "his hand", "his chest", "his voice",
        "his smile", "his lips", "his arms", "his face", "his gaze",
        "he said", "he murmured", "he whispered", "he growled",
        "he asked", "he replied", "he looked", "he was",
        "handsome", "he pulled me", "he kissed",
    ]
    male_pov_cues = [
        "her eyes", "her lips", "her hair", "her smile", "her face",
        "her voice", "her hand", "her dress", "her scent", "her body",
        "she said", "she murmured", "she whispered", "she laughed",
        "she asked", "she replied", "she looked", "she was",
        "beautiful", "gorgeous", "she blushed", "i kissed her",
    ]

    female_score = sum(1 for c in female_pov_cues if c in full_text)
    male_score = sum(1 for c in male_pov_cues if c in full_text)

    male_dialogue = 0
    female_dialogue = 0
    for seg in segments:
        if seg.get("type") == "dialogue":
            g = seg.get("speaker_gender", "unknown")
            if g == "male":
                male_dialogue += 1
            elif g == "female":
                female_dialogue += 1

    if male_dialogue > female_dialogue + 1:
        female_score += 2
    elif female_dialogue > male_dialogue + 1:
        male_score += 2

    if female_score > male_score:
        return "female"
    elif male_score > female_score:
        return "male"

    idx = paragraph.get("paragraph_index", 0)
    return "female" if idx % 2 == 0 else "male"


def assign_pov_to_segments(paragraphs: list[dict]) -> list[dict]:
    """Assign POV gender to all segments."""
    for paragraph in paragraphs:
        pov = detect_paragraph_pov(paragraph)
        for segment in paragraph.get("segments", []):
            segment["pov_gender"] = pov
    return paragraphs
