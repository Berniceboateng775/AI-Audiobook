"""
Audio Assembler Module
Stitches all generated speech segments together with proper timing,
pauses, background sounds, and transitions into one continuous audiobook.
"""

import os
from pydub import AudioSegment

from app.voice_engine import generate_segment_audio
from app.sound_effects import overlay_background, create_transition_sound


# Pause durations based on context (in milliseconds)
PAUSE_DURATIONS = {
    "sentence": 400,         # Between normal sentences
    "paragraph": 800,        # Between paragraphs
    "dialogue_start": 300,   # Before dialogue begins
    "dialogue_end": 300,     # After dialogue ends
    "scene_change": 1500,    # Between scene mood changes
    "dramatic": 1000,        # Before a dramatic/emotional line
    "chapter": 2500,         # Between chapters
}


def get_pause_duration(current_segment: dict, previous_segment: dict | None) -> int:
    """
    Determine pause duration based on segment context.
    
    Args:
        current_segment: Current segment being processed
        previous_segment: Previous segment (or None if first)
        
    Returns:
        Pause duration in milliseconds
    """
    if previous_segment is None:
        return 0

    # Scene mood change → longer pause
    prev_mood = previous_segment.get("scene_mood", "calm")
    curr_mood = current_segment.get("scene_mood", "calm")
    if prev_mood != curr_mood:
        return PAUSE_DURATIONS["scene_change"]

    # Switching between dialogue and narration
    prev_type = previous_segment.get("type", "narration")
    curr_type = current_segment.get("type", "narration")
    if prev_type != curr_type:
        if curr_type == "dialogue":
            return PAUSE_DURATIONS["dialogue_start"]
        else:
            return PAUSE_DURATIONS["dialogue_end"]

    # High-intensity emotion → dramatic pause before
    intensity = current_segment.get("emotion_intensity", "medium")
    if intensity == "high":
        return PAUSE_DURATIONS["dramatic"]

    # Default paragraph/sentence pause
    return PAUSE_DURATIONS["sentence"]


def assemble_paragraph(paragraph: dict) -> AudioSegment:
    """
    Assemble audio for a single paragraph with all its segments.
    
    Args:
        paragraph: Paragraph dict with 'segments' list
        
    Returns:
        Combined AudioSegment for the paragraph
    """
    segments = paragraph.get("segments", [])
    if not segments:
        return AudioSegment.silent(duration=500)

    combined = AudioSegment.empty()
    previous_segment = None

    for segment in segments:
        # Skip segments that are just attribution narration (already part of the flow)
        if segment.get("type") == "narration" and len(segment.get("text", "")) < 4:
            continue

        # Add pause between segments
        pause_ms = get_pause_duration(segment, previous_segment)
        if pause_ms > 0:
            combined += AudioSegment.silent(duration=pause_ms)

        # Generate speech for this segment
        try:
            speech = generate_segment_audio(segment)

            # Overlay background sound based on scene mood
            mood = segment.get("scene_mood", "calm")
            speech = overlay_background(speech, mood)

            combined += speech
            previous_segment = segment

        except Exception as e:
            print(f"  ⚠ Error generating audio for segment: {e}")
            # Add silence as placeholder
            combined += AudioSegment.silent(duration=1000)

    return combined


def assemble_audiobook(
    paragraphs: list[dict],
    output_path: str,
    output_format: str = "mp3"
) -> str:
    """
    Assemble the complete audiobook from analyzed paragraphs.
    
    Args:
        paragraphs: List of enriched paragraph dicts
        output_path: Path to save the final audio file
        output_format: Output format ("mp3" or "wav")
        
    Returns:
        Path to the generated audio file
    """
    print("\n🎧 Assembling audiobook...")
    print(f"  Processing {len(paragraphs)} paragraphs...\n")

    full_audio = AudioSegment.empty()
    previous_mood = None

    for i, paragraph in enumerate(paragraphs):
        segments = paragraph.get("segments", [])
        if not segments:
            continue

        # Check if scene mood changed (for transitions)
        current_mood = segments[0].get("scene_mood", "calm")
        if previous_mood and previous_mood != current_mood:
            transition = create_transition_sound(previous_mood, current_mood)
            full_audio += transition

        # Assemble paragraph audio
        paragraph_audio = assemble_paragraph(paragraph)
        full_audio += paragraph_audio

        # Add paragraph pause
        full_audio += AudioSegment.silent(duration=PAUSE_DURATIONS["paragraph"])

        previous_mood = current_mood

        # Progress update
        if (i + 1) % 5 == 0 or i == len(paragraphs) - 1:
            duration_sec = len(full_audio) / 1000
            print(f"  ✓ Paragraph {i + 1}/{len(paragraphs)} "
                  f"(total: {duration_sec:.1f}s)")

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # Export final audio
    print(f"\n  Exporting to {output_format.upper()}...")
    full_audio.export(output_path, format=output_format)

    duration_sec = len(full_audio) / 1000
    duration_min = duration_sec / 60
    print(f"\n  ✅ Audiobook saved: {output_path}")
    print(f"  📊 Duration: {duration_min:.1f} minutes ({duration_sec:.0f} seconds)")

    return output_path
