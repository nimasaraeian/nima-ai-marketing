# Railway deployment - explicit start command
# Entrypoint: api.app:app (canonical entrypoint that imports from api.main)
# This ensures we use the app with ALL routers included
web: uvicorn api.app:app --host 0.0.0.0 --port ${PORT:-8080} --timeout-keep-alive 75
