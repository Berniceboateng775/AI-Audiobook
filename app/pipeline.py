"""
Pipeline Orchestrator
Runs the full end-to-end audiobook generation pipeline:
PDF → Text → Analysis (Ollama) → Voice (pyttsx3) → Sound → Final Audio
"""

import os
import time

from app.pdf_extractor import extract_text, get_pdf_metadata
from app.text_cleaner import process_text
from app.dialogue_detector import process_paragraphs
from app.llm_analyzer import analyze_all_segments, check_ollama_status
from app.audio_assembler import assemble_audiobook
from app.voice_engine import assign_pov_to_segments


# Default output directory
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")


def process_book(
    pdf_path: str,
    output_filename: str | None = None,
    model: str = "mistral",
    use_llm: bool = True,
    output_format: str = "mp3",
    progress_callback=None
) -> str:
    """
    Full pipeline: PDF → Cinematic Audiobook
    
    Args:
        pdf_path: Path to the PDF storybook
        output_filename: Custom output filename (optional)
        model: Ollama model for text analysis
        use_llm: Whether to use LLM for analysis (False = rule-based only)
        output_format: Output audio format ("mp3" or "wav")
        progress_callback: Optional function(message: str) to report progress
        
    Returns:
        Path to the generated audiobook file
    """
    start_time = time.time()

    def report(msg: str):
        """Report progress to both console and callback."""
        print(f"  {msg}")
        if progress_callback:
            progress_callback(msg)

    print("=" * 60)
    print("AI CINEMATIC AUDIOBOOK ENGINE (Local Mode)")
    print("=" * 60)

    # ── STEP 1: Extract PDF ──────────────────────────────────
    report("📄 Extracting text from PDF...")
    metadata = get_pdf_metadata(pdf_path)
    print(f"  Book: {metadata.get('title', 'Unknown')}")
    print(f"  Author: {metadata.get('author', 'Unknown')}")
    print(f"  Pages: {metadata.get('page_count', '?')}")

    raw_text = extract_text(pdf_path)
    report(f"📄 Extracted {len(raw_text):,} characters from PDF")

    # ── STEP 2: Clean Text ───────────────────────────────────
    report("✂️ Cleaning and structuring text...")
    paragraphs = process_text(raw_text)
    total_sentences = sum(len(p["sentences"]) for p in paragraphs)
    report(f"✂️ Found {len(paragraphs)} paragraphs, {total_sentences} sentences")

    # ── STEP 3: Detect Dialogue ──────────────────────────────
    report("💬 Detecting dialogue and narration...")
    paragraphs = process_paragraphs(paragraphs)
    total_segments = sum(len(p["segments"]) for p in paragraphs)
    dialogue_count = sum(
        1 for p in paragraphs for s in p["segments"] if s["type"] == "dialogue"
    )
    narration_count = total_segments - dialogue_count
    report(f"💬 {dialogue_count} dialogue + {narration_count} narration segments")

    # ── STEP 4: LLM Analysis (Ollama) ────────────────────────
    if use_llm:
        report(f"🧠 Analyzing characters & emotions (Ollama — {model})...")
        if check_ollama_status():
            paragraphs = analyze_all_segments(
                paragraphs, model,
                full_text=raw_text,
                progress_callback=report
            )
        else:
            report("🧠 Ollama not available — using rule-based analysis")
            from app.llm_analyzer import apply_rule_based_analysis
            for p in paragraphs:
                p["segments"] = [apply_rule_based_analysis(s) for s in p["segments"]]
    else:
        report("🧠 Using rule-based analysis (LLM disabled)...")
        from app.llm_analyzer import apply_rule_based_analysis
        for p in paragraphs:
            p["segments"] = [apply_rule_based_analysis(s) for s in p["segments"]]

    # Print analysis summary
    emotions = {}
    for p in paragraphs:
        for s in p["segments"]:
            em = s.get("emotion", "neutral")
            emotions[em] = emotions.get(em, 0) + 1
    report(f"🧠 Emotion breakdown: {emotions}")

    # Character summary
    from app.llm_analyzer import get_character_registry
    characters = get_character_registry()
    if characters:
        report(f"🧠 Discovered {len(characters)} characters: {', '.join(characters.keys())}")

    # ── STEP 4.5: Detect POV per paragraph ──────────────────
    report("🎭 Detecting narrator POV gender per paragraph...")
    paragraphs = assign_pov_to_segments(paragraphs)

    # ── STEP 5 & 6: Generate Audio ──────────────────────────
    report("🎙️ Generating voices and assembling audio...")

    # Determine output path
    if output_filename is None:
        book_title = metadata.get("title", "audiobook")
        safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in book_title)
        safe_title = safe_title.strip() or "audiobook"
        output_filename = f"{safe_title}.{output_format}"

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    # Assemble the audiobook
    result_path = assemble_audiobook(paragraphs, output_path, output_format)

    # ── DONE ─────────────────────────────────────────────────
    elapsed = time.time() - start_time
    report(f"✅ Audiobook complete! ({elapsed:.1f}s)")
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

    if check_ollama_status():
        paragraphs = analyze_all_segments(paragraphs)
    else:
        from app.llm_analyzer import apply_rule_based_analysis
        for p in paragraphs:
            p["segments"] = [apply_rule_based_analysis(s) for s in p["segments"]]

    # Assign narrator POV gender
    paragraphs = assign_pov_to_segments(paragraphs)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, "test_output.mp3")

    return assemble_audiobook(paragraphs, output_path)
