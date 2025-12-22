# start.py
import os
import builtins

# --- HARD GUARANTEE: LOADER_DIR ALWAYS EXISTS ---
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
builtins.LOADER_DIR = os.environ.get(
    "LOADER_DIR",
    os.path.join(PROJECT_ROOT, "loaders")
)
builtins.LOADER_DIR = os.path.abspath(builtins.LOADER_DIR)
os.environ["LOADER_DIR"] = builtins.LOADER_DIR

print("BOOT OK | LOADER_DIR =", builtins.LOADER_DIR)

# --- NOW import the app ---
from api.main import app

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        app,  # Use the imported app directly, not string reference
        host="0.0.0.0",
        port=port,
        timeout_keep_alive=75,
        log_level="info",
    )
