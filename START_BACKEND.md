# 🚀 How to Start the Backend Server

## Quick Start

### Option 1: Using PowerShell Script (Recommended)
```powershell
cd N:\nima-ai-marketing
.\api\start_server.ps1
```

### Option 2: Using Batch File
```cmd
cd N:\nima-ai-marketing
.\api\run_server.bat
```

### Option 3: Manual Start
```powershell
cd N:\nima-ai-marketing
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```

## Verify Server is Running

Open a new terminal and run:
```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8000/health"
```

You should see: `{"status":"ok"}`

## Troubleshooting

### 1. Check if Python is installed
```powershell
python --version
```

### 2. Check if dependencies are installed
```powershell
cd N:\nima-ai-marketing
pip install -r api\requirements.txt
```

### 3. Check if .env file exists
```powershell
Test-Path N:\nima-ai-marketing\.env
```

The `.env` file should contain:
```
OPENAI_API_KEY=your-api-key-here
```

### 4. Check if port 8000 is already in use
```powershell
netstat -ano | findstr :8000
```

If something is using port 8000, either:
- Stop that process, or
- Use a different port (and update Next.js config accordingly)

## Expected Output

When the server starts successfully, you should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
============================================================
NIMA AI BRAIN API - Starting...
============================================================
System Prompt Length: XXXXX characters
Quality Engine: Enabled
============================================================
INFO:     Application startup complete.
```

## Next Steps

Once the backend is running:
1. ✅ The Next.js app should now be able to connect
2. ✅ Test the connection in your browser DevTools
3. ✅ You should see `[Brain API] Fetching: http://127.0.0.1:8000/api/brain/cognitive-friction` in the console











