from pathlib import Path

API_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = API_DIR / "artifacts"
DEBUG_SHOTS_DIR = API_DIR / "debug_shots"

ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
DEBUG_SHOTS_DIR.mkdir(parents=True, exist_ok=True)

