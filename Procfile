# Railway deployment - explicit start command
# Entrypoint: api.main:app (FastAPI app object defined in api/main.py)
web: uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8080} --timeout-keep-alive 75
