"""
Sound Effects Module
Maps scene moods to background sounds and handles sound layering.
Downloads and manages free sound effect files.
"""

import os
from pydub import AudioSegment


# Base directory for sound effects
SOUNDS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sounds")

# Scene mood → sound file mapping
MOOD_SOUNDS = {
    "romantic": "soft_piano.mp3",
    "action": "tension_drums.mp3",
    "suspense": "suspense_ambient.mp3",
    "calm": "nature_ambient.mp3",
    "dramatic": "dramatic_strings.mp3",
    "humorous": None,  # No background for humor (let dialogue breathe)
}

# Default volume reduction for background sounds (in dB)
BACKGROUND_VOLUME = -18  # Much quieter than dialogue


def get_available_sounds() -> list[str]:
    """
    List all available sound effect files.
    
    Returns:
        List of filenames in the sounds directory
    """
    if not os.path.exists(SOUNDS_DIR):
        os.makedirs(SOUNDS_DIR, exist_ok=True)
        return []

    return [f for f in os.listdir(SOUNDS_DIR)
            if f.endswith((".mp3", ".wav", ".ogg"))]


def get_background_sound(mood: str, duration_ms: int) -> AudioSegment | None:
    """
    Get a background sound for a scene mood, looped to the required duration.
    
    Args:
        mood: Scene mood (romantic, action, suspense, etc.)
        duration_ms: Required duration in milliseconds
        
    Returns:
        AudioSegment of background sound, or None if unavailable
    """
    sound_file = MOOD_SOUNDS.get(mood)

    if sound_file is None:
        return None

    sound_path = os.path.join(SOUNDS_DIR, sound_file)

    if not os.path.exists(sound_path):
        print(f"  Sound file not found: {sound_file} (skipping background sound)")
        return None

    try:
        sound = AudioSegment.from_file(sound_path)

        # Loop sound to match required duration
        if len(sound) < duration_ms:
            loops_needed = (duration_ms // len(sound)) + 1
            sound = sound * loops_needed

        # Trim to exact duration
        sound = sound[:duration_ms]

        # Reduce volume so it doesn't overpower dialogue
        sound = sound + BACKGROUND_VOLUME

        # Fade in and out for smooth transitions
        fade_ms = min(2000, duration_ms // 4)
        sound = sound.fade_in(fade_ms).fade_out(fade_ms)

        return sound

    except Exception as e:
        print(f"  Error loading sound {sound_file}: {e}")
        return None


def overlay_background(
    dialogue_audio: AudioSegment,
    mood: str
) -> AudioSegment:
    """
    Overlay background sound onto dialogue audio.
    
    Args:
        dialogue_audio: The main dialogue/narration audio
        mood: Scene mood for selecting background sound
        
    Returns:
        AudioSegment with background sound mixed in
    """
    background = get_background_sound(mood, len(dialogue_audio))

    if background is None:
        return dialogue_audio

    # Mix background under the dialogue
    return dialogue_audio.overlay(background)


def create_transition_sound(from_mood: str, to_mood: str, duration_ms: int = 1500) -> AudioSegment:
    """
    Create a smooth transition between scene moods.
    
    Args:
        from_mood: Previous scene mood
        to_mood: Next scene mood
        duration_ms: Transition duration
        
    Returns:
        AudioSegment for the transition
    """
    # If moods are the same, just return silence
    if from_mood == to_mood:
        return AudioSegment.silent(duration=500)

    # Create a brief silence with optional transition sound
    transition = AudioSegment.silent(duration=duration_ms)

    # Try to get the new mood's background and fade it in
    new_bg = get_background_sound(to_mood, duration_ms)
    if new_bg:
        new_bg = new_bg.fade_in(duration_ms)
        transition = transition.overlay(new_bg)

    return transition


def print_sound_setup_guide():
    """Print instructions for setting up sound effects."""
    print("""
╔══════════════════════════════════════════════════════╗
║           SOUND EFFECTS SETUP GUIDE                  ║
╠══════════════════════════════════════════════════════╣
║                                                      ║
║  Download FREE sounds from:                          ║
║  • https://pixabay.com/sound-effects/                ║
║  • https://mixkit.co/free-sound-effects/             ║
║  • https://freesound.org                             ║
║                                                      ║
║  Place them in the 'sounds/' folder as:              ║
║                                                      ║
║  sounds/                                             ║
║  ├── soft_piano.mp3       (romantic scenes)          ║
║  ├── tension_drums.mp3    (action scenes)            ║
║  ├── suspense_ambient.mp3 (suspense scenes)          ║
║  ├── nature_ambient.mp3   (calm scenes)              ║
║  └── dramatic_strings.mp3 (dramatic scenes)          ║
║                                                      ║
║  The system works WITHOUT sounds too — they're       ║
║  optional but make it cinematic!                     ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
    """)
