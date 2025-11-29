# Deployment Guide

## Render Deployment

This FastAPI application can be deployed on Render (or similar services) as a Python Web Service.

### Start Command

```bash
uvicorn api.main:app --host 0.0.0.0 --port $PORT
```

**Note:** Render automatically sets the `$PORT` environment variable. If deploying elsewhere, use:
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### Environment Variables

Make sure to set the following environment variables in your Render dashboard:

- `OPENAI_API_KEY` - Your OpenAI API key

### Health Check

The application includes a `/health` endpoint that returns `{"status": "ok"}` for monitoring.

### CORS Configuration

The API is configured to allow requests from:
- `https://nimasaraeian.com`
- `https://www.nimasaraeian.com`
- Local development origins (localhost)

### Module Path

- **Module:** `api.main`
- **App object:** `app`
- **Full path:** `api.main:app`

