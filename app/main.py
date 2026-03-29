"""
FastAPI Main Application
Web interface for the AI Cinematic Audiobook Engine.
"""

import os
import uuid
import time
import threading
from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.pipeline import process_book, OUTPUT_DIR


app = FastAPI(
    title="AI Cinematic Audiobook Engine",
    description="Transform PDF storybooks into dramatic, multi-voice audio performances",
    version="1.0.0"
)

# Directories
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

templates = Jinja2Templates(directory=TEMPLATE_DIR)

# Job tracking (in-memory for simplicity)
jobs: dict[str, dict] = {}


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the upload page."""
    return templates.TemplateResponse(name="index.html", request=request)


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload a PDF and start audiobook generation.
    Returns a job ID to track progress.
    """
    if not file.filename.endswith(".pdf"):
        return JSONResponse(
            status_code=400,
            content={"error": "Only PDF files are supported"}
        )

    # Save uploaded file
    job_id = str(uuid.uuid4())[:8]
    pdf_filename = f"{job_id}_{file.filename}"
    pdf_path = os.path.join(UPLOAD_DIR, pdf_filename)

    with open(pdf_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Initialize job with log history
    output_filename = f"{job_id}_audiobook.mp3"
    jobs[job_id] = {
        "status": "processing",
        "progress": "Starting...",
        "logs": [],
        "started_at": time.time(),
        "pdf_path": pdf_path,
        "pdf_name": file.filename,
        "output_filename": output_filename,
        "output_path": None,
        "error": None
    }

    # Run pipeline in background thread
    thread = threading.Thread(
        target=run_pipeline_job,
        args=(job_id, pdf_path, output_filename)
    )
    thread.start()

    return {"job_id": job_id, "message": "Processing started!"}


def run_pipeline_job(job_id: str, pdf_path: str, output_filename: str):
    """Run the audiobook pipeline in a background thread."""
    def update_progress(message: str):
        """Callback to update job progress — this feeds the frontend."""
        elapsed = time.time() - jobs[job_id]["started_at"]
        log_entry = f"[{elapsed:.1f}s] {message}"
        jobs[job_id]["progress"] = message
        jobs[job_id]["logs"].append(log_entry)
        print(f"  Job {job_id}: {log_entry}")

    try:
        update_progress("📄 Extracting text from PDF...")
        output_path = process_book(
            pdf_path=pdf_path,
            output_filename=output_filename,
            progress_callback=update_progress
        )
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["output_path"] = output_path
        jobs[job_id]["progress"] = "✅ Done!"
        jobs[job_id]["logs"].append(f"[{time.time() - jobs[job_id]['started_at']:.1f}s] ✅ Done!")

    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["progress"] = f"❌ Error: {str(e)}"
        jobs[job_id]["logs"].append(f"❌ Error: {str(e)}")
        print(f"Job {job_id} failed: {e}")
        import traceback
        traceback.print_exc()


@app.get("/status/{job_id}")
async def get_status(job_id: str):
    """Check the status of an audiobook generation job."""
    job = jobs.get(job_id)
    if not job:
        return JSONResponse(status_code=404, content={"error": "Job not found"})

    elapsed = time.time() - job["started_at"]

    return {
        "job_id": job_id,
        "status": job["status"],
        "progress": job["progress"],
        "logs": job.get("logs", []),
        "elapsed": round(elapsed, 1),
        "pdf_name": job["pdf_name"],
        "error": job.get("error")
    }


@app.get("/download/{job_id}")
async def download_audio(job_id: str):
    """Download the generated audiobook."""
    job = jobs.get(job_id)
    if not job:
        return JSONResponse(status_code=404, content={"error": "Job not found"})

    if job["status"] != "completed":
        return JSONResponse(
            status_code=400,
            content={"error": f"Job is {job['status']}, not ready for download"}
        )

    output_path = job["output_path"]
    if not output_path or not os.path.exists(output_path):
        return JSONResponse(status_code=404, content={"error": "Output file not found"})

    return FileResponse(
        path=output_path,
        media_type="audio/mpeg",
        filename=job["output_filename"]
    )
