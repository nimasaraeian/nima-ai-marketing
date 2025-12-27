from pathlib import Path
from api.core.config import get_artifacts_dir, get_debug_shots_dir

API_DIR = Path(__file__).resolve().parent

# Use centralized config functions that respect env vars
ARTIFACTS_DIR = get_artifacts_dir()
DEBUG_SHOTS_DIR = get_debug_shots_dir()

# Ensure directories exist (get_artifacts_dir already does this, but ensure here too)
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
DEBUG_SHOTS_DIR.mkdir(parents=True, exist_ok=True)

