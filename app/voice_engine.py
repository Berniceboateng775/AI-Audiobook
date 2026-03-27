"""
Voice Engine Module
Handles text-to-speech with multiple voices and emotional control.
Uses Coqui TTS (free, open-source) with multi-speaker support.
"""

import os
import tempfile
from pydub import AudioSegment

# TTS will be imported on first use (heavy import)
_tts_instance = None


def get_tts():
    """
    Lazy-load the TTS model (only loads once).
    Uses VCTK multi-speaker model for different male/female voices.
    """
    global _tts_instance

    if _tts_instance is None:
        print("Loading TTS model (first time may take a while)...")
        from TTS.api import TTS

        # VCTK model has 109 speakers with different genders/accents
        # This gives us distinct male and female voices
        try:
            _tts_instance = TTS(model_name="tts_models/en/vctk/vits", progress_bar=True)
            print("✓ Multi-speaker TTS model loaded (VCTK - 109 voices)")
        except Exception:
            # Fallback to single-speaker model
            print("Multi-speaker model failed, using single-speaker fallback...")
            _tts_instance = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC")
            print("✓ Single-speaker TTS model loaded (LJSpeech)")

    return _tts_instance


# Voice mapping: character types → speaker IDs
# VCTK speaker IDs — selected for distinct male/female/narrator voices
VOICE_MAP = {
    # Female voices (soft, emotional range)
    "female_default": "p225",   # Female, standard
    "female_soft": "p228",      # Female, softer tone
    "female_strong": "p229",    # Female, confident

    # Male voices (deep, varied)
    "male_default": "p226",     # Male, standard
    "male_deep": "p232",        # Male, deeper voice
    "male_strong": "p243",      # Male, commanding

    # Narrator voices
    "narrator": "p230",         # Neutral, clear voice
    "narrator_female": "p231",  # Female narrator
}

# Emotion → speech speed mapping
EMOTION_SPEED = {
    "neutral": 1.0,
    "anger": 1.15,        # Faster, sharper
    "sadness": 0.85,      # Slower, heavier
    "love": 0.9,          # Slower, tender
    "fear": 1.1,          # Slightly faster, nervous
    "excitement": 1.2,    # Fast, energetic
    "humor": 1.05,        # Slightly upbeat
    "suspense": 0.8,      # Slow, deliberate
}


def get_voice_id(gender: str, emotion: str = "neutral", speaking_style: str = "normal") -> str:
    """
    Map character attributes to a TTS speaker ID.
    
    Args:
        gender: "male", "female", or "narrator"
        emotion: Detected emotion
        speaking_style: Speaking style modifier
        
    Returns:
        Speaker ID string for TTS
    """
    if gender == "narrator":
        return VOICE_MAP["narrator"]

    if gender == "female":
        if speaking_style in ["whisper", "seductive", "trembling"]:
            return VOICE_MAP["female_soft"]
        elif speaking_style in ["shout", "cold"]:
            return VOICE_MAP["female_strong"]
        return VOICE_MAP["female_default"]

    if gender == "male":
        if speaking_style in ["shout", "cold"]:
            return VOICE_MAP["male_strong"]
        elif emotion in ["love", "sadness"]:
            return VOICE_MAP["male_deep"]
        return VOICE_MAP["male_default"]

    # Unknown gender defaults to narrator
    return VOICE_MAP["narrator"]


def generate_speech(
    text: str,
    gender: str = "narrator",
    emotion: str = "neutral",
    speaking_style: str = "normal"
) -> AudioSegment:
    """
    Generate speech audio from text with voice and emotion control.
    
    Args:
        text: Text to speak
        gender: "male", "female", or "narrator"
        emotion: Emotion for speed/tone adjustment
        speaking_style: Style modifier
        
    Returns:
        AudioSegment of the generated speech
    """
    tts = get_tts()

    # Get voice and speed settings
    voice_id = get_voice_id(gender, emotion, speaking_style)
    speed = EMOTION_SPEED.get(emotion, 1.0)

    # Generate to temp file
    temp_file = tempfile.mktemp(suffix=".wav")

    try:
        # Check if model supports multi-speaker
        if hasattr(tts, "speakers") and tts.speakers:
            tts.tts_to_file(
                text=text,
                file_path=temp_file,
                speaker=voice_id,
                speed=speed
            )
        else:
            # Single-speaker fallback
            tts.tts_to_file(
                text=text,
                file_path=temp_file,
                speed=speed
            )

        # Load generated audio
        audio = AudioSegment.from_wav(temp_file)

        # Apply post-processing based on speaking style
        audio = apply_style_effects(audio, speaking_style)

        return audio

    finally:
        # Clean up temp file
        if os.path.exists(temp_file):
            os.remove(temp_file)


def apply_style_effects(audio: AudioSegment, style: str) -> AudioSegment:
    """
    Apply audio effects based on speaking style.
    
    Args:
        audio: Raw speech audio
        style: Speaking style
        
    Returns:
        Modified AudioSegment
    """
    if style == "whisper":
        # Make quieter and slightly softer
        audio = audio - 6  # reduce volume by 6dB
        audio = audio.low_pass_filter(3000)  # soften high frequencies

    elif style == "shout":
        # Make louder and add emphasis
        audio = audio + 3  # boost volume by 3dB

    elif style == "trembling":
        # Slight volume reduction for vulnerability
        audio = audio - 3

    return audio


def generate_segment_audio(segment: dict) -> AudioSegment:
    """
    Generate audio for a fully analyzed segment.
    
    Args:
        segment: Enriched segment dict from llm_analyzer
        
    Returns:
        AudioSegment of the spoken segment
    """
    text = segment["text"]
    gender = segment.get("speaker_gender", "narrator")
    emotion = segment.get("emotion", "neutral")
    style = segment.get("speaking_style", "normal")

    return generate_speech(text, gender, emotion, style)
