"""
Voice Engine Module
Handles text-to-speech with multiple voices and emotional control.
Uses edge-tts (Microsoft Edge TTS) — FREE, no API key, high quality, multi-voice.
"""

import os
import asyncio
import tempfile
import edge_tts
from pydub import AudioSegment


# ══════════════════════════════════════════════════════════
# VOICE MAPPING — Microsoft Edge TTS voices
# These are all FREE and sound very realistic
# ══════════════════════════════════════════════════════════

VOICE_MAP = {
    # Female voices
    "female_default":  "en-US-JennyNeural",       # Warm, friendly female
    "female_soft":     "en-US-AriaNeural",         # Soft, expressive female
    "female_strong":   "en-US-MichelleNeural",     # Confident female

    # Male voices
    "male_default":    "en-US-GuyNeural",          # Standard male
    "male_deep":       "en-US-DavisNeural",        # Deep, smooth male
    "male_strong":     "en-US-JasonNeural",        # Strong, commanding male

    # Narrator voices
    "narrator":        "en-US-ChristopherNeural",  # Clear narrator voice
    "narrator_female": "en-US-SaraNeural",         # Female narrator
}

# Emotion → speech rate and pitch adjustments
EMOTION_SETTINGS = {
    "neutral":    {"rate": "+0%",  "pitch": "+0Hz"},
    "anger":      {"rate": "+15%", "pitch": "+2Hz"},     # Faster, slightly higher
    "sadness":    {"rate": "-15%", "pitch": "-3Hz"},     # Slower, lower
    "love":       {"rate": "-10%", "pitch": "-1Hz"},     # Slower, softer
    "fear":       {"rate": "+10%", "pitch": "+4Hz"},     # Faster, higher pitch
    "excitement": {"rate": "+20%", "pitch": "+3Hz"},     # Fast, energetic
    "humor":      {"rate": "+5%",  "pitch": "+2Hz"},     # Slightly upbeat
    "suspense":   {"rate": "-20%", "pitch": "-2Hz"},     # Very slow, deliberate
}

# Speaking style → volume adjustments
STYLE_VOLUME = {
    "normal":    0,
    "whisper":   -8,    # Much quieter
    "shout":     +4,    # Louder
    "trembling": -4,    # Slightly quieter
    "sarcastic": 0,
    "seductive": -5,    # Softer
    "cold":      0,
}


def get_voice_id(gender: str, emotion: str = "neutral", speaking_style: str = "normal") -> str:
    """
    Map character attributes to a TTS voice name.
    
    Args:
        gender: "male", "female", or "narrator"
        emotion: Detected emotion
        speaking_style: Speaking style modifier
        
    Returns:
        Edge TTS voice name
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
        elif emotion in ["love", "sadness", "suspense"]:
            return VOICE_MAP["male_deep"]
        return VOICE_MAP["male_default"]

    # Unknown gender defaults to narrator
    return VOICE_MAP["narrator"]


async def _generate_speech_async(
    text: str,
    voice: str,
    rate: str,
    pitch: str,
    output_path: str
):
    """Internal async function to generate speech with edge-tts."""
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await communicate.save(output_path)


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
        emotion: Emotion for rate/pitch adjustment
        speaking_style: Style modifier for volume effects
        
    Returns:
        AudioSegment of the generated speech
    """
    # Get voice and emotion settings
    voice = get_voice_id(gender, emotion, speaking_style)
    settings = EMOTION_SETTINGS.get(emotion, EMOTION_SETTINGS["neutral"])

    # Generate to temp file
    temp_file = tempfile.mktemp(suffix=".mp3")

    try:
        # Run async edge-tts
        asyncio.run(_generate_speech_async(
            text=text,
            voice=voice,
            rate=settings["rate"],
            pitch=settings["pitch"],
            output_path=temp_file
        ))

        # Load generated audio
        audio = AudioSegment.from_mp3(temp_file)

        # Apply volume adjustments based on speaking style
        volume_adj = STYLE_VOLUME.get(speaking_style, 0)
        if volume_adj != 0:
            audio = audio + volume_adj

        # Apply additional effects for specific styles
        if speaking_style == "whisper":
            audio = audio.low_pass_filter(3000)  # Soften highs for whisper effect

        return audio

    except Exception as e:
        print(f"  ⚠ TTS error: {e}")
        # Return 1 second of silence as fallback
        return AudioSegment.silent(duration=1000)

    finally:
        # Clean up temp file
        if os.path.exists(temp_file):
            os.remove(temp_file)


def generate_segment_audio(segment: dict) -> AudioSegment:
    """
    Generate audio for a fully analyzed text segment.
    
    Args:
        segment: Enriched segment dict from llm_analyzer
        
    Returns:
        AudioSegment of the spoken segment
    """
    text = segment["text"]
    gender = segment.get("speaker_gender", "narrator")
    emotion = segment.get("emotion", "neutral")
    style = segment.get("speaking_style", "normal")

    # Map "unknown" gender to narrator
    if gender == "unknown":
        gender = "narrator"

    return generate_speech(text, gender, emotion, style)


async def list_available_voices():
    """List all available edge-tts voices (useful for debugging)."""
    voices = await edge_tts.list_voices()
    english_voices = [v for v in voices if v["Locale"].startswith("en-")]

    print(f"\n🎙️ Available English voices ({len(english_voices)}):\n")
    for v in english_voices:
        print(f"  {v['ShortName']:30s} | {v['Gender']:8s} | {v['Locale']}")

    return english_voices
