# AI Brain API - Quick Start Guide

## 🚀 Start Server

```powershell
cd C:\Users\USER\Desktop\tensorflow-nima
python -m uvicorn api.app:app --host localhost --port 8000
```

Server will be available at: `http://localhost:8000`

## 🧪 Test API

```powershell
python api/test_chat.py
```

## 📡 API Endpoints

### Health Check
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health" -Method GET
```

### Chat Endpoint
```powershell
$body = @{
    message = "Your question here"
    model = "gpt-4"
    temperature = 0.7
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/chat" -Method POST -Body $body -ContentType "application/json"
```

## ⚙️ Configuration

Make sure `.env` file exists in project root with:
```
OPENAI_API_KEY=your-api-key-here
```

## 📝 Example Response

The API uses the complete AI Brain system prompt, including:
- Core Brain (role, thinking protocol, personality)
- Nima Memory (profile, expertise)
- Domain Memory (AI Marketing, Psychology, CRO)
- Action Memory (operating patterns)
- Action Engine (task breakdown)
- Quality Engine (quality checks)

All responses follow these protocols automatically.





