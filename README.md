# 🎭 AI Cinematic Audiobook Engine

> Transform PDF storybooks into dramatic, multi-voice audio performances — like a movie, but audio only.

The engine reads your story, detects characters and emotions, assigns unique male/female voices, and generates a cinematic audiobook with background sounds and emotional acting.

## ✨ Features

- 📄 **PDF Extraction** — Upload any storybook in PDF format
- 💬 **Dialogue Detection** — Automatically separates speech from narration
- 🧠 **Emotion Analysis** — Detects anger, love, fear, excitement, suspense via Ollama LLM
- 🎙️ **Multi-Voice TTS** — Different voices for male, female characters and narrator
- 🎭 **Emotional Acting** — Whispers, shouts, trembling voices based on context
- 🎶 **Background Sounds** — Cinematic ambient sounds matched to scene mood
- ⏱️ **Smart Timing** — Dramatic pauses, scene transitions, natural pacing

## 🛠️ Tech Stack (100% Free)

| Component | Tool |
|-----------|------|
| PDF Extraction | PyMuPDF |
| Text Cleaning | spaCy + NLTK |
| LLM Analysis | Ollama (Mistral) |
| Text-to-Speech | edge-tts (Microsoft Neural Voices — FREE) |
| Audio Processing | pydub + FFmpeg |
| Web API | FastAPI |
| Frontend | Vanilla HTML/CSS/JS |

## 📋 Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com) — for local LLM
- [FFmpeg](https://ffmpeg.org) — for audio processing

## 🚀 Setup

```bash
# 1. Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Download spaCy model
python -m spacy download en_core_web_sm

# 4. Download NLTK data
python -c "import nltk; nltk.download('punkt_tab')"

# 5. Pull Ollama model (make sure Ollama is running)
ollama pull mistral

# 6. (Optional) Add sound effects to sounds/ folder
# Download free sounds from pixabay.com/sound-effects/
```

## ▶️ Usage

### Web Interface
```bash
uvicorn app.main:app --reload
# Open http://localhost:8000
```

### Command Line
```python
from app.pipeline import process_book, quick_test

# Full book
process_book("path/to/your/book.pdf")

# Quick test (first 3 paragraphs only)
quick_test("path/to/your/book.pdf")
```

## 📁 Project Structure

```
AI Audiobook/
├── app/
│   ├── main.py              # FastAPI web app
│   ├── pipeline.py          # Full pipeline orchestrator
│   ├── pdf_extractor.py     # PDF → text
│   ├── text_cleaner.py      # Text cleaning & splitting
│   ├── dialogue_detector.py # Dialogue vs narration
│   ├── llm_analyzer.py      # Ollama emotion/character analysis
│   ├── voice_engine.py      # Coqui TTS multi-voice
│   ├── sound_effects.py     # Background sound mapping
│   └── audio_assembler.py   # Final audio stitching
├── templates/
│   └── index.html           # Web upload UI
├── sounds/                  # Background sound effects
├── output/                  # Generated audiobooks
├── requirements.txt
└── README.md
```

## 🎧 Processing Pipeline

```
PDF → Extract Text → Clean → Detect Dialogue → Analyze Emotions → Generate Voices → Add Sounds → Assemble → Final Audio 🎧
```