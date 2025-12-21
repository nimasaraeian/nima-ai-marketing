"""
Run API server with automatic .env loading.

This script ensures .env is loaded before starting the server.
"""

import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load .env file before importing anything else
project_root = Path(__file__).parent
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file, override=True)
    print(f"✅ Loaded .env from {env_file}")
else:
    # Try api/.env as fallback
    api_env = project_root / "api" / ".env"
    if api_env.exists():
        load_dotenv(api_env, override=True)
        print(f"✅ Loaded .env from {api_env}")
    else:
        load_dotenv()  # Load from current directory or system env
        print("⚠️  No .env file found, using system environment variables")


def main():
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    import uvicorn
    
    print("\n🚀 Starting Nima AI Brain API server...")
    print("   Server will be available at: http://127.0.0.1:8000")
    print("   Health check: http://127.0.0.1:8000/health")
    print("   Debug env (local only): http://127.0.0.1:8000/debug/env\n")
    
    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=False, log_level="info")


if __name__ == "__main__":
    main()







