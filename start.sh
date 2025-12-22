#!/bin/sh
set -e

PORT="${PORT:-8000}"

echo "Starting FastAPI on PORT=$PORT"
echo "Trying common ASGI app paths..."

CANDIDATES="
main:app
api.main:app
app.main:app
src.main:app
api.app:app
app.api:app
"

for TARGET in $CANDIDATES; do
  echo ">> Trying: $TARGET"
  python -c "import importlib; m,p='$TARGET'.split(':'); importlib.import_module(m)" >/dev/null 2>&1 || {
    echo "   - module not found: $TARGET"
    continue
  }

  # If module import works, try running uvicorn. If it crashes immediately, try next.
  # exec will replace the shell process; so we only exec after a quick sanity check.
  python -c "import importlib; m,p='$TARGET'.split(':'); mod=importlib.import_module(m); getattr(mod,p)" >/dev/null 2>&1 || {
    echo "   - attribute not found: $TARGET"
    continue
  }

  echo "✅ Found valid ASGI target: $TARGET"
  exec uvicorn "$TARGET" --host 0.0.0.0 --port "$PORT" --timeout-keep-alive 75
done

echo "❌ Could not find ASGI app. Checked candidates:"
echo "$CANDIDATES"
echo "Tip: search for 'app = FastAPI(' in your code and tell me the file path."
exit 1
