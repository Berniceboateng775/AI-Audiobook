"""
Sound Effects Module
Maps scene moods to background sounds and handles sound layering.
"""

import os
from pydub import AudioSegment


SOUNDS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sounds")

# Scene mood → sound file mapping (expanded for cinematic variety)
MOOD_SOUNDS = {
    # Core moods
    "romantic":   "soft_piano.mp3",
    "love":       "soft_piano.mp3",
    "intimate":   "night_crickets.mp3",
    
    # Calm/neutral
    "calm":       "nature_ambient.mp3",
    "peaceful":   "nature_ambient.mp3",
    "neutral":    "nature_ambient.mp3",
    
    # Tension and suspense
    "suspense":   "suspense_ambient.mp3",
    "tense":      "suspense_ambient.mp3",
    "mystery":    "suspense_ambient.mp3",
    
    # Action/chaos
    "action":     "tension_drums.mp3",
    "fight":      "chaos.mp3",
    "chaos":      "chaos.mp3",
    "battle":     "chaos.mp3",
    
    # Dramatic/emotional
    "dramatic":   "dramatic_strings.mp3",
    "emotional":  "dramatic_strings.mp3",
    "intense":    "heartbeat.mp3",
    "heartbreak": "heartbeat.mp3",
    
    # Weather
    "rain":       "rain.mp3",
    "rainy":      "rain.mp3",
    "storm":      "thunder_storm.mp3",
    "thunder":    "thunder_storm.mp3",
    "wind":       "wind_storm.mp3",
    "stormy":     "thunder_storm.mp3",
    
    # Social
    "party":      "crowd_murmur.mp3",
    "crowd":      "crowd_murmur.mp3",
    "social":     "crowd_murmur.mp3",
    "gala":       "crowd_murmur.mp3",
    
    # Dark/horror
    "dark":       "eerie.mp3",
    "horror":     "eerie.mp3",
    "eerie":      "eerie.mp3",
    "creepy":     "eerie.mp3",
    
    # Night
    "night":      "night_crickets.mp3",
    "quiet":      "night_crickets.mp3",
    
    # Humor — no background (let dialogue breathe)
    "humorous":   None,
    "humor":      None,
    "funny":      None,
}

BACKGROUND_VOLUME = -18
_warned_sounds = set()


def get_available_sounds() -> list[str]:
    """List all available sound effect files."""
    if not os.path.exists(SOUNDS_DIR):
        os.makedirs(SOUNDS_DIR, exist_ok=True)
        return []
    return [f for f in os.listdir(SOUNDS_DIR) if f.endswith((".mp3", ".wav", ".ogg"))]


def get_background_sound(mood: str, duration_ms: int) -> AudioSegment | None:
    """Get background sound for a scene mood, looped to required duration."""
    sound_file = MOOD_SOUNDS.get(mood)

    if sound_file is None:
        return None

    sound_path = os.path.join(SOUNDS_DIR, sound_file)

    if not os.path.exists(sound_path):
        if sound_file not in _warned_sounds:
            print(f"  Sound not found: {sound_file} (run: python generate_sounds.py)")
            _warned_sounds.add(sound_file)
        return None

    try:
        sound = AudioSegment.from_file(sound_path)

        # Loop to match duration
        if len(sound) < duration_ms:
            loops = (duration_ms // len(sound)) + 1
            sound = sound * loops

        sound = sound[:duration_ms]
        sound = sound + BACKGROUND_VOLUME

        # Smooth fades
        fade_ms = min(2000, duration_ms // 4)
        sound = sound.fade_in(fade_ms).fade_out(fade_ms)

        return sound

    except Exception as e:
        print(f"  Error loading sound {sound_file}: {e}")
        return None


def overlay_background(dialogue_audio: AudioSegment, mood: str) -> AudioSegment:
    """Overlay background sound onto dialogue audio."""
    background = get_background_sound(mood, len(dialogue_audio))
    if background is None:
        return dialogue_audio
    return dialogue_audio.overlay(background)


def create_transition_sound(from_mood: str, to_mood: str, duration_ms: int = 1500) -> AudioSegment:
    """Create a smooth transition between scene moods."""
    if from_mood == to_mood:
        return AudioSegment.silent(duration=500)

    transition = AudioSegment.silent(duration=duration_ms)
    new_bg = get_background_sound(to_mood, duration_ms)
    if new_bg:
        new_bg = new_bg.fade_in(duration_ms)
        transition = transition.overlay(new_bg)

    return transition
