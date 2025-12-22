#!/usr/bin/env python3
"""
Startup script for Railway deployment.
Reads PORT from environment and starts uvicorn server.
"""
import os
import sys

# Get PORT from environment, default to 8000
# IMPORTANT: Convert to int to ensure it's a valid integer
port_str = os.getenv("PORT", "8000")
try:
    port = int(port_str)
except (ValueError, TypeError):
    print(f"ERROR: Invalid PORT value: '{port_str}'. Using default 8000.")
    port = 8000

print("=" * 50)
print("Starting NIMA AI Marketing API...")
print("=" * 50)
print(f"PORT is: {port} (type: {type(port).__name__})")
print(f"PORT from env: '{port_str}'")
print(f"Python version: {sys.version}")
print(f"Working directory: {os.getcwd()}")
print("=" * 50)

# Start uvicorn
# IMPORTANT: Pass port as string (uvicorn expects string)
cmd = [
    "uvicorn",
    "api.main:app",
    "--host", "0.0.0.0",
    "--port", str(port),  # Convert to string for uvicorn
    "--timeout-keep-alive", "75",
    "--access-log"
]

print(f"Executing: {' '.join(cmd)}")
print("=" * 50)

try:
    os.execvp("uvicorn", cmd)
except FileNotFoundError:
    print("ERROR: uvicorn not found. Make sure it's installed.")
    print("Install with: pip install uvicorn[standard]")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: Failed to start server: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

