# AI Cinematic Audiobook Engine

> Transform PDF storybooks into dramatic, multi-voice audio performances — like a movie, but audio only.

The engine reads your story, detects characters and emotions, assigns unique male/female voices, and generates a cinematic audiobook with background sounds and emotional acting.

## Features

- **PDF Extraction** — Upload any storybook in PDF format
- **Dialogue Detection** — Automatically separates speech from narration
- **Character Detection** — Identifies individual characters by name and assigns unique voices
- **Emotion Analysis** — Detects anger, love, fear, excitement, suspense via Ollama LLM (Mistral)
- **Multi-Voice TTS** — Chatterbox AI voices with 20 unique per-character voice profiles
- **Emotional Acting** — Whispers, shouts, trembling voices based on context
- **Background Sounds** — Cinematic ambient sounds matched to scene mood
- **Smart Timing** — Dramatic pauses, scene transitions, natural pacing

## Tech Stack (100% Free)

| Component | Tool |
|-----------|------|
| PDF Extraction | PyMuPDF |
| Text Cleaning | NLTK |
| LLM Analysis | **Ollama (Mistral)** — local, free, no API key needed |
| Text-to-Speech | **Chatterbox TTS** (HuggingFace API) — free, AI voice synthesis |
| TTS Fallback | pyttsx3 (local Windows voices) → gTTS (Google) |
| Audio Processing | pydub + FFmpeg |
| Web API | FastAPI |
| Frontend | Vanilla HTML/CSS/JS |

## Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com) — local LLM runtime (free)
- [FFmpeg](https://ffmpeg.org) — for audio processing

## Setup

```bash
# 1. Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Download NLTK data
python -c "import nltk; nltk.download('punkt_tab')"

# 4. Install Ollama & pull Mistral model
#    Download Ollama from https://ollama.com
ollama pull mistral

# 5. (Optional) Add voice reference clips to voices/ folder
#    .wav/.mp3 files named: narrator_male, narrator_female,
#    female_lead, male_lead, female_soft, male_strong, etc.

# 6. (Optional) Add sound effects to sounds/ folder
```

## Running the App

### Terminal 1 — Start Ollama (keep running)
```bash
ollama serve
```

### Terminal 2 — Start the web server
```bash
venv\Scripts\activate
venv\Scripts\python -m uvicorn app.main:app --reload
# Open http://localhost:8000
```

### Command Line (alternative)
```python
from app.pipeline import process_book, quick_test

# Full book
process_book("path/to/your/book.pdf")

# Quick test (first 3 paragraphs only)
quick_test("path/to/your/book.pdf")
```

## Project Structure

```
AI Audiobook/
├── app/
│   ├── main.py              # FastAPI web app
│   ├── pipeline.py          # Full pipeline orchestrator
│   ├── pdf_extractor.py     # PDF → text
│   ├── text_cleaner.py      # Text cleaning & splitting
│   ├── dialogue_detector.py # Dialogue vs narration detection
│   ├── llm_analyzer.py      # Ollama (Mistral) character + emotion analysis
│   ├── voice_engine.py      # Chatterbox TTS with per-character voices
│   ├── sound_effects.py     # Background sound mapping
│   └── audio_assembler.py   # Final audio stitching
├── templates/
│   └── index.html           # Web upload UI
├── voices/                  # Voice reference clips (optional)
├── sounds/                  # Background sound effects
├── output/                  # Generated audiobooks
├── requirements.txt
└── README.md
```

## Processing Pipeline

```
PDF → Extract Text → Clean → Detect Dialogue → Analyze Characters & Emotions (Ollama) → Generate Voices (Chatterbox) → Add Sounds → Assemble → Final Audio
```

## How Character Voices Work

The engine discovers character names from the text and assigns each a **unique voice profile**:

1. **Rule-based analysis** scans attribution tags ("said John", "Mary whispered") to extract names
2. **Ollama (Mistral)** identifies characters in ambiguous dialogue segments
3. Each character gets a unique combo of Chatterbox TTS parameters:
   - `exaggeration` — how expressive the voice is
   - `temperature` — voice variation/naturalness
   - `cfg` — guidance strength

This means even a book with 20+ characters will have **distinct-sounding voices** for each one.