from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from agno.agent import Agent
from agno.models.groq import Groq
from groq import Groq as GroqClient
from dotenv import load_dotenv
import os
from typing import Optional
import tempfile
from mangum import Mangum



# Load environment variables from .env file
load_dotenv()

app = FastAPI(
    title="SciTalk API",
    description="AI-powered voice transcription and scientific text processing API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """API health check and information endpoint."""
    return {
        "name": "SciTalk API",
        "version": "1.0.0",
        "status": "online",
        "features": {
            "transcription": "Groq Whisper Large v3",
            "ai_model": "Llama 3.3 70B (via Groq)",
            "capabilities": [
                "Real-time voice transcription",
                "Scientific terminology recognition",
                "Chemical formula formatting",
                "Unit standardization",
                "Experiment logging",
                "Voice command detection"
            ]
        },
        "endpoints": {
            "production": {
                "POST /api/transcribe": "Upload audio for transcription",
                "POST /api/process-command": "Process text with AI analysis"
            },
            "demo_testing": {
                "GET /api/demo/samples": "List all demo endpoints",
                "GET /api/demo/sample-audio": "Download sample audio file",
                "POST /api/demo/test-transcribe": "Transcribe sample audio",
                "POST /api/demo/full-workflow": "Complete demo workflow"
            },
            "documentation": {
                "GET /docs": "Interactive API docs (Swagger UI)",
                "GET /redoc": "Alternative API documentation"
            }
        },
        "quick_test": {
            "description": "Test the API with sample audio",
            "command": "curl -X POST http://localhost:8000/api/demo/full-workflow"
        }
    }

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Initialize Groq client
groq_client = GroqClient(api_key=GROQ_API_KEY)

voice_agent = Agent(
    name="Scientific Voice Command Assistant",
    model=Groq(id="llama-3.3-70b-versatile"),
    description="""You are an AI assistant specialized in processing scientific voice commands and transcriptions.
    
    CRITICAL: Use HTML subscript and superscript tags for chemical formulas:
    - Use <sub> for subscripts: H<sub>2</sub>O, CO<sub>2</sub>, H<sub>2</sub>SO<sub>4</sub>
    - Use <sup> for superscripts: Ca<sup>2+</sup>, O<sup>2-</sup>
    
    Your responsibilities:
    1. Recognize and properly format scientific terminology, chemical formulas, and units
    2. Identify experimental procedures and lab commands from speech
    3. Structure scientific observations in a clear, organized format
    4. Auto-format chemical formulas with HTML tags (e.g., "H two O" → H<sub>2</sub>O)
    5. Standardize units (e.g., "milliliters" → mL, "degrees celsius" → °C)
    6. Detect and process voice commands for experiment logging
    7. Structure data with clear markdown sections
    
    When processing scientific text:
    - ALWAYS use <sub></sub> tags for subscripts in chemical formulas
    - ALWAYS use <sup></sup> tags for superscripts in ions
    - Use markdown headers (###) for section organization
    - Standardize scientific units and notation
    - Organize with clear sections: Introduction, Procedure, Observations, Measurements, Conclusions
    - Preserve numerical precision
    - Use **bold** for important terms and measurements
    
    Respond in clean HTML + markdown format for proper rendering.""",
    markdown=True,
    instructions=[
        "ALWAYS format chemical formulas with HTML: H<sub>2</sub>O NOT H2O or H₂O",
        "Use <sub> for all subscripts and <sup> for all superscripts",
        "Standardize all units to abbreviated forms (mL, °C, mg, etc.)",
        "Use ### for section headers (Introduction, Procedure, Observations, etc.)",
        "Use **bold** for important measurements and key terms",
        "Preserve all numerical values with their original precision",
        "Keep formatting clean and professional for scientific documentation"
    ]
)

@app.post("/api/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    try:
        # Save uploaded file temporarily
        audio_bytes = await file.read()
        
        # Create a temporary file with the audio data
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
            temp_audio.write(audio_bytes)
            temp_audio_path = temp_audio.name
        
        # Use Groq's Whisper API for transcription
        with open(temp_audio_path, "rb") as audio_file:
            transcription = groq_client.audio.transcriptions.create(
                file=(temp_audio_path, audio_file.read()),
                model="whisper-large-v3",
                temperature=0,
                response_format="verbose_json"
            )
        
        # Clean up temp file
        os.unlink(temp_audio_path)
        
        return {"text": transcription.text, "confidence": 0.95}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/process-command")
async def process_command(payload: dict):
    """Process scientific voice commands with context-aware AI analysis."""
    text = payload.get("text", "")
    command_type = detect_command(text)
    
    # Add context based on command type with HTML formatting emphasis
    context_prompts = {
        "START_EXPERIMENT": "This is the start of an experiment. Format with:\n### Introduction\nExtract experiment details, objectives, and initial conditions. Use HTML tags for any chemical formulas (<sub></sub> for subscripts).",
        "ADD_OBSERVATION": "Format this observation scientifically:\n### Observations\nInclude what was observed, conditions, and measurements. Use **bold** for key terms and <sub></sub> for chemical formula subscripts.",
        "RECORD_MEASUREMENT": "Extract all measurements:\n### Measurements\nFormat with proper units (mL, °C, mg). Use **bold** for values. Organize in a clear list.",
        "FORMAT_CHEMICAL": "Format all chemical formulas with HTML tags. Example: H<sub>2</sub>O, CO<sub>2</sub>, H<sub>2</sub>SO<sub>4</sub>. Use <sup></sup> for charges.",
        "PROCEDURE": "Structure as a scientific procedure:\n### Procedure\nUse numbered steps. Include any chemical formulas with <sub></sub> tags.",
        "ANALYZE_DATA": "Analyze the scientific data:\n### Analysis\nLook for patterns, trends, or significant findings. Use **bold** for key conclusions.",
        "SAFETY_NOTE": "⚠️ **SAFETY NOTE**\nHighlight this as a critical safety consideration. Make it prominent and clear.",
        "GENERAL_SCIENTIFIC": "Process this scientific text:\n- Format chemical formulas with <sub></sub> tags\n- Use ### for section headers\n- Use **bold** for important terms\n- Standardize units"
    }
    
    prompt = f"{context_prompts.get(command_type, 'Process this scientific text with proper HTML formatting for chemistry.')}\n\n{text}"
    response = voice_agent.run(prompt)
    
    return {
        "original_text": text,
        "processed_text": response.content,
        "detected_command": command_type,
    }

@app.get("/api/demo/sample-audio")
async def get_sample_audio():
    """Download sample audio file for testing."""
    audio_path = "recording-1760707486163.webm"
    
    if not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail="Sample audio file not found")
    
    return FileResponse(
        audio_path,
        media_type="audio/webm",
        filename="sample-recording.webm"
    )

@app.post("/api/demo/test-transcribe")
async def demo_test_transcribe():
    """Test transcription using the sample audio file."""
    audio_path = "recording-1760707486163.webm"
    
    if not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail="Sample audio file not found")
    
    try:
        # Use the sample audio file for transcription
        with open(audio_path, "rb") as audio_file:
            transcription = groq_client.audio.transcriptions.create(
                file=(audio_path, audio_file.read()),
                model="whisper-large-v3",
                temperature=0,
                response_format="verbose_json"
            )
        
        return {
            "demo": True,
            "text": transcription.text,
            "confidence": 0.95,
            "note": "This is a real transcription from the sample audio file"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/demo/full-workflow")
async def demo_full_workflow():
    """Demo complete workflow: transcribe sample audio + AI processing."""
    audio_path = "recording-1760707486163.webm"
    
    if not os.path.exists(audio_path):
        # Fallback to sample text if audio not available
        text = "Start experiment: Acid-base titration. Add observation: Solution changed from clear to pink at 24.5 milliliters. Record measurement: pH 7.2, temperature 22 degrees celsius."
        confidence = 0.95
        using_audio = False
    else:
        try:
            # Transcribe the actual audio file
            with open(audio_path, "rb") as audio_file:
                transcription = groq_client.audio.transcriptions.create(
                    file=(audio_path, audio_file.read()),
                    model="whisper-large-v3",
                    temperature=0,
                    response_format="verbose_json"
                )
            text = transcription.text
            confidence = 0.95
            using_audio = True
        except Exception as e:
            # Fallback on error
            text = "Error transcribing sample audio. Using fallback text."
            confidence = 0.0
            using_audio = False
    
    # Process with AI
    command_type = detect_command(text)
    
    context_prompts = {
        "START_EXPERIMENT": "This is the start of an experiment. Format with:\n### Introduction\nExtract experiment details, objectives, and initial conditions. Use HTML tags for any chemical formulas (<sub></sub> for subscripts).",
        "ADD_OBSERVATION": "Format this observation scientifically:\n### Observations\nInclude what was observed, conditions, and measurements. Use **bold** for key terms and <sub></sub> for chemical formula subscripts.",
        "RECORD_MEASUREMENT": "Extract all measurements:\n### Measurements\nFormat with proper units (mL, °C, mg). Use **bold** for values. Organize in a clear list.",
        "FORMAT_CHEMICAL": "Format all chemical formulas with HTML tags. Example: H<sub>2</sub>O, CO<sub>2</sub>, H<sub>2</sub>SO<sub>4</sub>. Use <sup></sup> for charges.",
        "PROCEDURE": "Structure as a scientific procedure:\n### Procedure\nUse numbered steps. Include any chemical formulas with <sub></sub> tags.",
        "ANALYZE_DATA": "Analyze the scientific data:\n### Analysis\nLook for patterns, trends, or significant findings. Use **bold** for key conclusions.",
        "SAFETY_NOTE": "⚠️ **SAFETY NOTE**\nHighlight this as a critical safety consideration. Make it prominent and clear.",
        "GENERAL_SCIENTIFIC": "Process this scientific text:\n- Format chemical formulas with <sub></sub> tags\n- Use ### for section headers\n- Use **bold** for important terms\n- Standardize units"
    }
    
    prompt = f"{context_prompts.get(command_type, 'Process this scientific text with proper HTML formatting for chemistry.')}\n\n{text}"
    response = voice_agent.run(prompt)
    
    return {
        "demo": True,
        "using_sample_audio": using_audio,
        "transcription": {
            "text": text,
            "confidence": confidence
        },
        "ai_analysis": {
            "original_text": text,
            "processed_text": response.content,
            "detected_command": command_type
        }
    }

@app.get("/api/demo/samples")
async def get_demo_samples():
    """Get list of available demo endpoints and sample data."""
    return {
        "demo_endpoints": {
            "GET /api/demo/sample-audio": "Download the sample audio file",
            "POST /api/demo/test-transcribe": "Transcribe the sample audio file",
            "POST /api/demo/full-workflow": "Complete demo: transcribe + AI process sample audio",
            "GET /api/demo/samples": "This endpoint - list all demos"
        },
        "sample_text_examples": [
            {
                "id": 1,
                "name": "Acid-Base Titration",
                "text": "Start experiment: Acid-base titration. Add observation: Solution changed from clear to pink at 24.5 milliliters. Record measurement: pH 7.2, temperature 22 degrees celsius.",
                "command": "START_EXPERIMENT"
            },
            {
                "id": 2,
                "name": "Chemical Safety",
                "text": "Safety note: Always add acid to water, never water to acid. Add observation: Mixed sulfuric acid H two S O four with water at 0.5 molar concentration.",
                "command": "SAFETY_NOTE"
            },
            {
                "id": 3,
                "name": "Enzyme Activity",
                "text": "Procedure: Measure enzyme activity. Step one: Prepare substrate at 37 degrees celsius. Add observation: Rapid bubbling when catalase added to hydrogen peroxide H two O two.",
                "command": "PROCEDURE"
            }
        ],
        "usage": {
            "test_audio": "curl -X POST http://localhost:8000/api/demo/test-transcribe",
            "full_demo": "curl -X POST http://localhost:8000/api/demo/full-workflow",
            "download_audio": "curl -O http://localhost:8000/api/demo/sample-audio"
        }
    }

def detect_command(text: str) -> Optional[str]:
    """Detect scientific voice commands from transcribed text."""
    lower = text.lower()
    
    # Experiment control commands
    if "start experiment" in lower or "begin experiment" in lower:
        return "START_EXPERIMENT"
    if "end experiment" in lower or "stop experiment" in lower:
        return "END_EXPERIMENT"
    
    # Data recording commands
    if "add observation" in lower or "record observation" in lower:
        return "ADD_OBSERVATION"
    if "record measurement" in lower or "log measurement" in lower:
        return "RECORD_MEASUREMENT"
    if "note" in lower or "add note" in lower:
        return "ADD_NOTE"
    
    # Formatting commands
    if "save" in lower and "timestamp" in lower:
        return "SAVE_AND_TIMESTAMP"
    if "format" in lower and ("formula" in lower or "chemical" in lower):
        return "FORMAT_CHEMICAL"
    
    # Procedure commands
    if "procedure" in lower or "method" in lower:
        return "PROCEDURE"
    if "step" in lower:
        return "ADD_STEP"
    
    # Analysis commands
    if "analyze" in lower or "analysis" in lower:
        return "ANALYZE_DATA"
    if "summarize" in lower or "summary" in lower:
        return "SUMMARIZE"
    if "conclusion" in lower:
        return "ADD_CONCLUSION"
    
    # Safety and warnings
    if "safety" in lower or "hazard" in lower or "warning" in lower:
        return "SAFETY_NOTE"
    
    return "GENERAL_SCIENTIFIC"
# Lambda handler
handler = Mangum(app)