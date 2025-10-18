# 🎤 SciTalk Backend API

AI-powered voice transcription and scientific text processing API.

## 🚀 Quick Start

### Local Development

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set environment variable
export GROQ_API_KEY=your_groq_api_key_here

# 3. Run the server
uvicorn app:app --reload

# 4. Access API at http://localhost:8000
```

### AWS Lambda Deployment

```bash
# 1. Set your Groq API key
export GROQ_API_KEY=your_groq_api_key_here

# 2. Deploy to Lambda
./deploy-lambda.sh

# 3. API will be available at the Lambda Function URL
```

## 📋 Requirements

- **Python:** 3.11+
- **Groq API Key:** [Get one free](https://console.groq.com)

## 🎯 API Endpoints

### Production Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/transcribe` | Upload audio file for transcription |
| `POST` | `/api/process-command` | Process text with AI analysis |

### Demo/Testing Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/demo/samples` | List all demo endpoints |
| `GET` | `/api/demo/sample-audio` | Download sample audio file |
| `POST` | `/api/demo/test-transcribe` | Transcribe sample audio |
| `POST` | `/api/demo/full-workflow` | Complete demo workflow |

### Documentation

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | API info and health check |
| `GET` | `/docs` | Interactive API docs (Swagger UI) |
| `GET` | `/redoc` | Alternative API documentation |

## 💡 Usage Examples

### 1. Transcribe Audio

```bash
curl -X POST http://localhost:8000/api/transcribe \
  -F "file=@recording.webm" \
  -H "Accept: application/json"
```

**Response:**
```json
{
  "text": "Start experiment: Acid-base titration...",
  "confidence": 0.95
}
```

### 2. Process Scientific Text

```bash
curl -X POST http://localhost:8000/api/process-command \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Add observation: Mixed H two S O four with water at 25 milliliters"
  }'
```

**Response:**
```json
{
  "original_text": "Add observation: Mixed H two S O four...",
  "processed_text": "### Observations\n\nMixed H<sub>2</sub>SO<sub>4</sub> with water at **25 mL**...",
  "detected_command": "ADD_OBSERVATION"
}
```

### 3. Test with Demo

```bash
# Run complete workflow with sample audio
curl -X POST http://localhost:8000/api/demo/full-workflow | jq
```

## 🧪 Supported Scientific Commands

| Command | Trigger Words | Action |
|---------|--------------|--------|
| `START_EXPERIMENT` | "start experiment", "begin experiment" | Format experiment details |
| `ADD_OBSERVATION` | "add observation", "record observation" | Structure observations |
| `RECORD_MEASUREMENT` | "record measurement", "log measurement" | Format measurements with units |
| `PROCEDURE` | "procedure", "method", "step" | Create numbered procedures |
| `SAFETY_NOTE` | "safety", "hazard", "warning" | Highlight safety information |
| `ANALYZE_DATA` | "analyze", "analysis" | Analyze scientific data |
| `GENERAL_SCIENTIFIC` | (default) | Format chemical formulas and units |

## 🔬 AI Capabilities

### Chemical Formula Formatting
- **Input:** "H two O", "C O two", "H two S O four"
- **Output:** H<sub>2</sub>O, CO<sub>2</sub>, H<sub>2</sub>SO<sub>4</sub>

### Unit Standardization
- **Input:** "milliliters", "degrees celsius", "milligrams"
- **Output:** mL, °C, mg

### Structured Output
- Markdown headers (###)
- Bold emphasis (**bold**)
- Organized sections (Procedure, Observations, Measurements, Conclusions)
- Proper scientific notation

## 🤝 API Integration

### Python Example
```python
import requests

# Transcribe audio
with open("audio.webm", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/transcribe",
        files={"file": f}
    )
    transcription = response.json()
    print(transcription["text"])

# Process with AI
response = requests.post(
    "http://localhost:8000/api/process-command",
    json={"text": "Start experiment: pH measurement"}
)
analysis = response.json()
print(analysis["processed_text"])
```

### JavaScript Example
```javascript
// Transcribe audio
const formData = new FormData();
formData.append('file', audioBlob, 'audio.webm');

const response = await fetch('http://localhost:8000/api/transcribe', {
  method: 'POST',
  body: formData
});
const { text } = await response.json();

// Process with AI
const aiResponse = await fetch('http://localhost:8000/api/process-command', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ text })
});
const analysis = await aiResponse.json();
```

## 🚀 AWS Lambda Deployment (Docker Container)

### Prerequisites

- AWS CLI installed and configured (`aws configure`)
- Docker installed
- AWS account with Lambda and ECR permissions

### Quick Deploy

```bash
# Set your Groq API key
export GROQ_API_KEY=your_groq_api_key_here

# Run deployment script
./deploy-lambda.sh
```

### Manual Deployment

```bash
# 1. Build Docker image
docker build --platform linux/amd64 -t scitalk-backend .

# 2. Authenticate with ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# 3. Tag and push image
docker tag scitalk-backend:latest \
  YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/scitalk-backend:latest

docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/scitalk-backend:latest

# 4. Create/Update Lambda function
aws lambda update-function-code \
  --function-name scitalk-backend \
  --image-uri YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/scitalk-backend:latest
```

## 🛠️ Installation & Setup

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/scitalk.git
cd scitalk/backend
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
# Create .env file
cat > .env << EOF
GROQ_API_KEY=your_groq_api_key_here
EOF
```

### 4. Run Server

**Development:**
```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

**Production:**
```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

## 📁 Project Structure

```
backend/
├── app.py                    # Main FastAPI application
├── lambda_handler.py         # AWS Lambda handler
├── requirements.txt          # Python dependencies
├── Dockerfile               # AWS Lambda container configuration
├── deploy-lambda.sh         # Automated deployment script
├── .env                     # Environment variables (create this)
├── .gitignore              # Git ignore rules
└── README.md               # This file
```

## 🔧 Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | Yes | - | Your Groq API key |
| `HOST` | No | `0.0.0.0` | Server host |
| `PORT` | No | `8000` | Server port |

### API Models

- **Transcription:** `whisper-large-v3` (Groq)
- **AI Processing:** `llama-3.3-70b-versatile` (Groq)

