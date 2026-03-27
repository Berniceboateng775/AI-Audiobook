"""
Voice Engine Module
Uses pyttsx3 (offline Windows SAPI voices) for distinct male/female voices.
Falls back to gTTS (Google) if SAPI voices unavailable.

- David = deep male voice (narrator/dialogue)
- Zira = female voice (narrator/dialogue)
- Rate/volume adjustments for emotional expression
"""

import os
import tempfile
import shutil
import pyttsx3
from pydub import AudioSegment
import threading


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
# TTS ENGINE SETUP
# ══════════════════════════════════════════════════════════

# Thread lock — pyttsx3 is NOT thread-safe
_tts_lock = threading.Lock()

# Discover available SAPI voices once at startup
_voice_ids = {}
try:
    _engine = pyttsx3.init()
    _voices = _engine.getProperty('voices')
    for v in _voices:
        name_lower = v.name.lower()
        if 'david' in name_lower:
            _voice_ids['male'] = v.id
        elif 'zira' in name_lower:
            _voice_ids['female'] = v.id
    _engine.stop()
    del _engine
    print(f"  SAPI voices found: {list(_voice_ids.keys())}")
except Exception as e:
    print(f"  pyttsx3 init warning: {e}")

# Base speaking rate (words per minute)
BASE_RATE = 175


# ══════════════════════════════════════════════════════════
# EMOTION → VOICE ADJUSTMENTS
# ══════════════════════════════════════════════════════════

EMOTION_SETTINGS = {
    "neutral":     {"rate_mult": 1.0,  "vol": 1.0},
    "anger":       {"rate_mult": 1.15, "vol": 1.0},
    "sadness":     {"rate_mult": 0.85, "vol": 0.8},
    "love":        {"rate_mult": 0.90, "vol": 0.85},
    "fear":        {"rate_mult": 1.10, "vol": 0.75},
    "excitement":  {"rate_mult": 1.20, "vol": 1.0},
    "humor":       {"rate_mult": 1.05, "vol": 0.95},
    "suspense":    {"rate_mult": 0.80, "vol": 0.85},
    "frustration": {"rate_mult": 1.10, "vol": 1.0},
    "surprise":    {"rate_mult": 1.15, "vol": 1.0},
    "self-doubt":  {"rate_mult": 0.90, "vol": 0.8},
}

STYLE_VOLUME_DB = {
    "normal": 0, "whisper": -8, "shout": +5, "trembling": -4,
    "sarcastic": 0, "seductive": -5, "cold": -2,
}


def get_voice_gender(segment: dict) -> str:
    """Determine which voice gender to use for a segment."""
    gender = segment.get("speaker_gender", "narrator")
    seg_type = segment.get("type", "narration")

    # Dialogue: use speaker gender
    if seg_type == "dialogue":
        if gender == "female":
            return "female"
        elif gender == "male":
            return "male"
        # Unknown gender → use POV
        pov = segment.get("pov_gender", "male")
        return pov

    # Narration: use POV gender
    pov = segment.get("pov_gender", "male")
    return pov


def generate_speech_pyttsx3(text: str, gender: str, emotion: str = "neutral") -> AudioSegment:
    """Generate speech using pyttsx3 (Windows SAPI voices)."""
    text = text.strip()
    if len(text) < 2:
        return AudioSegment.silent(duration=300)

    voice_id = _voice_ids.get(gender, _voice_ids.get("male") or _voice_ids.get("female"))
    if not voice_id:
        return _generate_speech_gtts(text)

    settings = EMOTION_SETTINGS.get(emotion, EMOTION_SETTINGS["neutral"])
    rate = int(BASE_RATE * settings["rate_mult"])
    volume = settings["vol"]

    temp_file = tempfile.mktemp(suffix=".wav")

    try:
        with _tts_lock:
            engine = pyttsx3.init()
            engine.setProperty('voice', voice_id)
            engine.setProperty('rate', rate)
            engine.setProperty('volume', volume)
            engine.save_to_file(text, temp_file)
            engine.runAndWait()
            engine.stop()
            del engine

        if not os.path.exists(temp_file) or os.path.getsize(temp_file) < 100:
            return AudioSegment.silent(duration=500)

        audio = AudioSegment.from_wav(temp_file)
        return audio

    except Exception as e:
        print(f"  TTS error: {e}")
        return AudioSegment.silent(duration=500)
    finally:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except OSError:
                pass


def _generate_speech_gtts(text: str) -> AudioSegment:
    """Fallback: Google TTS (requires internet, one voice only)."""
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


def generate_speech(text, voice=None, emotion="neutral", speaking_style="normal"):
    """Generate speech — main entry point."""
    text = text.strip()
    if len(text) < 2:
        return AudioSegment.silent(duration=300)

    gender = "male"
    if voice and ("jenny" in voice.lower() or "aria" in voice.lower() or
                  "michelle" in voice.lower() or "sara" in voice.lower()):
        gender = "female"

    audio = generate_speech_pyttsx3(text, gender, emotion)

    # Apply style volume
    vol = STYLE_VOLUME_DB.get(speaking_style, 0)
    if vol != 0:
        audio = audio + vol
    if speaking_style == "whisper":
        audio = audio.low_pass_filter(3000)

    return audio


def generate_segment_audio(segment: dict) -> AudioSegment:
    """Generate audio for a fully analyzed segment."""
    text = segment.get("text", "").strip()
    if not text or len(text) < 2:
        return AudioSegment.silent(duration=200)

    gender = get_voice_gender(segment)
    emotion = segment.get("emotion", "neutral")
    style = segment.get("speaking_style", "normal")

    audio = generate_speech_pyttsx3(text, gender, emotion)

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

    # Narrator describes male → POV is female
    female_pov_cues = [
        "his eyes", "his jaw", "his hand", "his chest", "his voice",
        "his smile", "his lips", "his arms", "his face", "his gaze",
        "he said", "he murmured", "he whispered", "he growled",
        "he asked", "he replied", "he looked", "he was",
        "handsome", "he pulled me", "he kissed",
    ]
    # Narrator describes female → POV is male
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

    # Default: alternate
    idx = paragraph.get("paragraph_index", 0)
    return "female" if idx % 2 == 0 else "male"


def assign_pov_to_segments(paragraphs: list[dict]) -> list[dict]:
    """Assign POV gender to all segments."""
    for paragraph in paragraphs:
        pov = detect_paragraph_pov(paragraph)
        for segment in paragraph.get("segments", []):
            segment["pov_gender"] = pov
    return paragraphs
