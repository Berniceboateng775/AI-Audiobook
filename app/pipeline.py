"""
Pipeline Orchestrator
Runs the full end-to-end audiobook generation pipeline:
PDF → Text → Analysis (Groq) → Voice (edge-tts) → Sound → Final Audio
"""

import os
import time

from app.pdf_extractor import extract_text, get_pdf_metadata
from app.text_cleaner import process_text
from app.dialogue_detector import process_paragraphs
from app.llm_analyzer import analyze_all_segments, check_groq_status
from app.audio_assembler import assemble_audiobook
from app.sound_effects import print_sound_setup_guide


# Default output directory
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")


def process_book(
    pdf_path: str,
    output_filename: str | None = None,
    model: str = "llama-3.3-70b-versatile",
    use_llm: bool = True,
    output_format: str = "mp3"
) -> str:
    """
    Full pipeline: PDF → Cinematic Audiobook
    
    Args:
        pdf_path: Path to the PDF storybook
        output_filename: Custom output filename (optional)
        model: Groq model for text analysis
        use_llm: Whether to use LLM for analysis (False = rule-based only)
        output_format: Output audio format ("mp3" or "wav")
        
    Returns:
        Path to the generated audiobook file
    """
    start_time = time.time()

    print("=" * 60)
    print("AI CINEMATIC AUDIOBOOK ENGINE")
    print("=" * 60)

    # ── STEP 1: Extract PDF ──────────────────────────────────
    print("\nSTEP 1: Extracting text from PDF...")
    metadata = get_pdf_metadata(pdf_path)
    print(f"  Book: {metadata.get('title', 'Unknown')}")
    print(f"  Author: {metadata.get('author', 'Unknown')}")
    print(f"  Pages: {metadata.get('page_count', '?')}")

    raw_text = extract_text(pdf_path)
    print(f"  Extracted {len(raw_text):,} characters")

    # ── STEP 2: Clean Text ───────────────────────────────────
    print("\nSTEP 2: Cleaning and structuring text...")
    paragraphs = process_text(raw_text)
    total_sentences = sum(len(p["sentences"]) for p in paragraphs)
    print(f"  Found {len(paragraphs)} paragraphs, {total_sentences} sentences")

    # ── STEP 3: Detect Dialogue ──────────────────────────────
    print("\nSTEP 3: Detecting dialogue and narration...")
    paragraphs = process_paragraphs(paragraphs)
    total_segments = sum(len(p["segments"]) for p in paragraphs)
    dialogue_count = sum(
        1 for p in paragraphs for s in p["segments"] if s["type"] == "dialogue"
    )
    narration_count = total_segments - dialogue_count
    print(f"  {dialogue_count} dialogue segments, {narration_count} narration segments")

    # ── STEP 4: LLM Analysis (Groq) ─────────────────────────
    if use_llm:
        print("\nSTEP 4: Analyzing emotions and characters (Groq)...")
        if check_groq_status():
            paragraphs = analyze_all_segments(paragraphs, model)
        else:
            print("  Groq not available — using rule-based fallback")
            from app.llm_analyzer import apply_fallback_analysis
            for p in paragraphs:
                p["segments"] = [apply_fallback_analysis(s) for s in p["segments"]]
    else:
        print("\nSTEP 4: Using rule-based analysis (LLM disabled)...")
        from app.llm_analyzer import apply_fallback_analysis
        for p in paragraphs:
            p["segments"] = [apply_fallback_analysis(s) for s in p["segments"]]

    # Print analysis summary
    emotions = {}
    for p in paragraphs:
        for s in p["segments"]:
            em = s.get("emotion", "neutral")
            emotions[em] = emotions.get(em, 0) + 1

    print(f"  Emotion breakdown: {emotions}")

    # ── STEP 5 & 6: Generate Audio ──────────────────────────
    print("\nSTEP 5: Generating voices and assembling audio...")

    # Determine output path
    if output_filename is None:
        book_title = metadata.get("title", "audiobook")
        # Clean filename
        safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in book_title)
        safe_title = safe_title.strip() or "audiobook"
        output_filename = f"{safe_title}.{output_format}"

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    # Assemble the audiobook
    result_path = assemble_audiobook(paragraphs, output_path, output_format)

    # ── DONE ─────────────────────────────────────────────────
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print("AUDIOBOOK GENERATION COMPLETE!")
    print(f"  File: {result_path}")
    print(f"  Time: {elapsed:.1f} seconds")
    print("=" * 60)

    return result_path


def quick_test(pdf_path: str, max_paragraphs: int = 3) -> str:
    """
    Quick test: process only the first few paragraphs of a book.
    Useful for testing the pipeline without waiting for the full book.
    
    Args:
        pdf_path: Path to the PDF
        max_paragraphs: Number of paragraphs to process
        
    Returns:
        Path to the test audio file
    """
    print(f"\nQUICK TEST MODE (first {max_paragraphs} paragraphs)\n")

    raw_text = extract_text(pdf_path)
    paragraphs = process_text(raw_text)[:max_paragraphs]
    paragraphs = process_paragraphs(paragraphs)

    if check_groq_status():
        paragraphs = analyze_all_segments(paragraphs)
    else:
        from app.llm_analyzer import apply_fallback_analysis
        for p in paragraphs:
            p["segments"] = [apply_fallback_analysis(s) for s in p["segments"]]

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, "test_output.mp3")

    return assemble_audiobook(paragraphs, output_path)
