"""
Voice Engine Module — OVERHAULED for quality
Uses edge-tts with SSML for expressive, cinematic voice performance.
Features:
- POV-aware narrator gender (female narration for female scenes)
- Deep, distinct male/female voices
- SSML prosody for emotional expression
- Consistent voice per character
"""

import os
import sys
import subprocess
import tempfile
import shutil
from pydub import AudioSegment


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
    for search_dir in search_paths:
        ffmpeg_path = os.path.join(search_dir, "ffmpeg.exe")
        if os.path.exists(ffmpeg_path):
            os.environ["PATH"] = search_dir + ";" + os.environ.get("PATH", "")
            AudioSegment.converter = ffmpeg_path
            ffprobe_path = os.path.join(search_dir, "ffprobe.exe")
            if os.path.exists(ffprobe_path):
                AudioSegment.ffprobe = ffprobe_path
            print(f"  Found ffmpeg at: {search_dir}")
            return
    # Try recursive WinGet search
    winget_dir = os.path.expanduser(r"~\AppData\Local\Microsoft\WinGet\Packages")
    if os.path.exists(winget_dir):
        for root, dirs, files in os.walk(winget_dir):
            if "ffmpeg.exe" in files:
                os.environ["PATH"] = root + ";" + os.environ.get("PATH", "")
                AudioSegment.converter = os.path.join(root, "ffmpeg.exe")
                if "ffprobe.exe" in files:
                    AudioSegment.ffprobe = os.path.join(root, "ffprobe.exe")
                print(f"  Found ffmpeg at: {root}")
                return

_find_ffmpeg()


# ══════════════════════════════════════════════════════════
# VOICE MAPPING — Carefully chosen for distinct, rich voices
# ══════════════════════════════════════════════════════════

VOICE_MAP = {
    # Female voices — warm, expressive
    "female_1":     "en-US-JennyNeural",       # Warm, emotional (main female)
    "female_2":     "en-US-AriaNeural",         # Soft, breathy (whispers/love)
    "female_3":     "en-US-MichelleNeural",     # Strong, confident

    # Male voices — deep, commanding
    "male_1":       "en-US-DavisNeural",        # Deep, smooth (main male - DEEPEST)
    "male_2":       "en-US-GuyNeural",          # Standard male
    "male_3":       "en-US-JasonNeural",        # Strong, commanding

    # Narrator voices  
    "narrator_male":   "en-US-ChristopherNeural",  # Clear male narrator
    "narrator_female": "en-US-JennyNeural",         # Clear female narrator
}


# ══════════════════════════════════════════════════════════
# EMOTION → SSML PROSODY SETTINGS (much more expressive)
# ══════════════════════════════════════════════════════════

EMOTION_SSML = {
    "neutral":    {"rate": "0%",   "pitch": "0%",   "volume": "medium"},
    "anger":      {"rate": "15%",  "pitch": "5%",   "volume": "loud"},
    "sadness":    {"rate": "-20%", "pitch": "-8%",  "volume": "soft"},
    "love":       {"rate": "-15%", "pitch": "-3%",  "volume": "soft"},
    "fear":       {"rate": "10%",  "pitch": "10%",  "volume": "x-soft"},
    "excitement": {"rate": "20%",  "pitch": "8%",   "volume": "loud"},
    "humor":      {"rate": "5%",   "pitch": "5%",   "volume": "medium"},
    "suspense":   {"rate": "-25%", "pitch": "-5%",  "volume": "soft"},
}

STYLE_VOLUME_DB = {
    "normal": 0, "whisper": -10, "shout": +5, "trembling": -5,
    "sarcastic": 0, "seductive": -7, "cold": -2,
}


def get_voice_for_segment(segment: dict) -> str:
    """
    Smart voice selection based on gender, type, and context.
    Uses POV-aware narrator voice (female narrator for female scenes).
    """
    gender = segment.get("speaker_gender", "narrator")
    seg_type = segment.get("type", "narration")
    style = segment.get("speaking_style", "normal")
    emotion = segment.get("emotion", "neutral")

    # NARRATION — use the POV narrator voice
    if seg_type == "narration" or gender == "narrator":
        pov = segment.get("pov_gender", "male")
        if pov == "female":
            return VOICE_MAP["narrator_female"]
        return VOICE_MAP["narrator_male"]

    # FEMALE DIALOGUE
    if gender == "female":
        if style in ["whisper", "seductive", "trembling"]:
            return VOICE_MAP["female_2"]  # Soft, breathy Aria
        elif style in ["shout", "cold"]:
            return VOICE_MAP["female_3"]  # Strong Michelle
        return VOICE_MAP["female_1"]  # Main female Jenny

    # MALE DIALOGUE — always use deep voice as primary
    if gender == "male":
        if style in ["shout", "cold"]:
            return VOICE_MAP["male_3"]  # Commanding Jason
        return VOICE_MAP["male_1"]  # Deep Davis (ALWAYS deep for male)

    # Unknown → use paragraph POV narrator
    pov = segment.get("pov_gender", "male")
    if pov == "female":
        return VOICE_MAP["narrator_female"]
    return VOICE_MAP["narrator_male"]


def generate_speech(text, voice, emotion="neutral", speaking_style="normal"):
    """
    Generate speech using edge-tts CLI subprocess.
    Adjusts rate and pitch based on emotion.
    """
    text = text.strip()
    if len(text) < 2:
        return AudioSegment.silent(duration=300)

    # Get emotion settings
    settings = EMOTION_SSML.get(emotion, EMOTION_SSML["neutral"])

    temp_file = tempfile.mktemp(suffix=".mp3")

    try:
        cmd = [
            sys.executable, "-m", "edge_tts",
            "--voice", voice,
            "--rate", f"+{settings['rate']}" if not settings['rate'].startswith('-') else settings['rate'],
            "--pitch", f"+{settings['pitch']}" if not settings['pitch'].startswith('-') else settings['pitch'],
            "--text", text,
            "--write-media", temp_file
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            return AudioSegment.silent(duration=500)

        if not os.path.exists(temp_file) or os.path.getsize(temp_file) < 100:
            return AudioSegment.silent(duration=500)

        audio = AudioSegment.from_mp3(temp_file)

        # Apply volume adjustments for speaking style
        vol = STYLE_VOLUME_DB.get(speaking_style, 0)
        if vol != 0:
            audio = audio + vol

        # Whisper: low-pass filter for softer highs
        if speaking_style == "whisper":
            audio = audio.low_pass_filter(3000)

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


def generate_segment_audio(segment: dict) -> AudioSegment:
    """Generate audio for a fully analyzed text segment with smart voice selection."""
    text = segment.get("text", "").strip()
    if not text or len(text) < 2:
        return AudioSegment.silent(duration=200)

    voice = get_voice_for_segment(segment)
    emotion = segment.get("emotion", "neutral")
    style = segment.get("speaking_style", "normal")

    return generate_speech(text, voice, emotion, style)


# ══════════════════════════════════════════════════════════
# POV DETECTION — Determines narrator gender per paragraph
# ══════════════════════════════════════════════════════════

def detect_paragraph_pov(paragraph: dict) -> str:
    """
    Detect the point-of-view gender for a paragraph.
    In romance novels, narration between dialogue is from the POV character.
    
    Strategy:
    - Check dialogue gender distribution in this paragraph
    - Check for first-person pronouns + gendered cues
    - Use majority gender of nearby characters
    """
    segments = paragraph.get("segments", [])
    full_text = paragraph.get("text", "").lower()
    
    # First-person female cues in narration
    female_pov_cues = [
        "my dress", "my heels", "my hair", "my lipstick", "my purse",
        "i adjusted my", "my heart raced", "my chest tightened",
        "i blushed", "my cheeks", "he was", "he looked", "his eyes",
        "his jaw", "his hand", "his chest", "he said", "he murmured",
        "he whispered", "he growled", "handsome", "his smile",
        "he pulled me", "he kissed me",
    ]
    
    # First-person male cues in narration  
    male_pov_cues = [
        "my tie", "my suit", "clenched my fist", "my jaw",
        "she was", "she looked", "her eyes", "her lips", "her hair",
        "her smile", "she said", "she whispered", "she murmured",
        "beautiful", "gorgeous", "she blushed", "her dress",
        "i pulled her", "i kissed her", "her scent",
    ]
    
    female_score = sum(1 for cue in female_pov_cues if cue in full_text)
    male_score = sum(1 for cue in male_pov_cues if cue in full_text)
    
    # Also check dialogue genders — if most dialogue is male,
    # the POV is likely female (opposite gender = who they're talking to)
    dialogue_genders = {"male": 0, "female": 0}
    for seg in segments:
        if seg.get("type") == "dialogue":
            g = seg.get("speaker_gender", "unknown")
            if g in dialogue_genders:
                dialogue_genders[g] += 1
    
    # More male dialogue speakers → POV is likely female (and vice versa)
    if dialogue_genders["male"] > dialogue_genders["female"] + 2:
        female_score += 3
    elif dialogue_genders["female"] > dialogue_genders["male"] + 2:
        male_score += 3
    
    if female_score > male_score:
        return "female"
    elif male_score > female_score:
        return "male"
    
    return "female"  # Default to female for romance novels


def assign_pov_to_segments(paragraphs: list[dict]) -> list[dict]:
    """
    Assign POV gender to all segments in all paragraphs.
    This determines which voice reads the narration.
    """
    for paragraph in paragraphs:
        pov = detect_paragraph_pov(paragraph)
        for segment in paragraph.get("segments", []):
            segment["pov_gender"] = pov
    
    return paragraphs
