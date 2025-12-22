# Railway Deployment Configuration

## Entrypoint
- **Module Path**: `api.app:app` (CANONICAL - use this)
- **File**: `api/app.py` (imports app from `api.main`)
- **FastAPI App Object**: `app` (from `api.main`)
- **Note**: `api.app.py` is a wrapper that ensures we use the complete app with ALL routers

## Start Command

### Option 1: Using Procfile (Recommended)
Railway will automatically use the `Procfile` if present:
```
web: uvicorn api.app:app --host 0.0.0.0 --port ${PORT:-8080} --timeout-keep-alive 75
```

### Option 2: Custom Start Command in Railway Settings
If Procfile is not used, set Custom Start Command to:
```
uvicorn api.app:app --host 0.0.0.0 --port $PORT
```

### Option 3: Using Dockerfile
If using Dockerfile, it uses `start.sh` which runs:
```bash
uvicorn api.app:app --host 0.0.0.0 --port "$PORT" --timeout-keep-alive 75
```

**IMPORTANT**: Always use `api.app:app` (not `api.main:app`) to ensure the canonical entrypoint is used.

## Static File Mounts

The app mounts two directories for serving screenshots:

1. **`/api/artifacts`** - Screenshots from `analyze_url_human` endpoint
   - Directory: `/app/api/artifacts` (in container)
   - Health: `GET /api/artifacts/_health`

2. **`/api/debug_shots`** - Screenshots from `decision-engine` endpoint
   - Directory: `/app/api/debug_shots` (in container)
   - Health: `GET /api/debug_shots/_health`

Both mounts are defined in `api/main.py` (lines 179-180) **BEFORE** any `include_router` calls to ensure they work correctly.

## Health Endpoints

- `GET /health` - Main health check (returns `{"status": "ok"}`)
- `GET /api/artifacts/_health` - Artifacts directory health
- `GET /api/debug_shots/_health` - Debug shots directory health

## Verification

After deployment, verify:

1. Build info (verify correct module):
   ```bash
   curl https://<your-domain>/api/_build
   # Should return: {"module":"api.main", "app_file":"/app/api/main.py", ...}
   ```

2. Health check works:
   ```bash
   curl https://<your-domain>/health
   # Should return: {"status":"ok"}
   ```

3. Artifacts mount works:
   ```bash
   curl https://<your-domain>/api/artifacts/_health
   # Should return: {"exists":true, "is_dir":true, "path":"...", "sample_files":[...]}
   ```

4. Debug shots mount works:
   ```bash
   curl https://<your-domain>/api/debug_shots/_health
   # Should return: {"exists":true, "is_dir":true, "path":"...", "sample_files":[...]}
   ```

5. OpenAPI includes endpoints:
   ```bash
   curl https://<your-domain>/openapi.json | grep -i "artifacts/_health"
   # Should show the endpoint in the schema
   
   curl https://<your-domain>/openapi.json | grep -i "analyze/url-human"
   # Should show the endpoint
   
   curl https://<your-domain>/openapi.json | grep -i "decision-engine/report-from-url"
   # Should show the endpoint
   ```

## Port Configuration

Railway automatically sets the `PORT` environment variable. The app:
- Binds to `0.0.0.0` (all interfaces) - **REQUIRED for Railway**
- Uses `$PORT` from environment
- Falls back to `8080` if `PORT` is not set

## Troubleshooting

### 502 Bad Gateway
- Ensure start command uses `--host 0.0.0.0` (not `127.0.0.1`)
- Verify `$PORT` is being used (check Railway logs)
- Check that `/health` endpoint returns 200

### 404 on /api/artifacts/_health
- Verify mounts are defined BEFORE `include_router` calls
- Check that `ARTIFACTS_DIR` and `DEBUG_SHOTS_DIR` are correctly resolved
- Ensure directories exist (they are auto-created on startup)

### Mounts not working
- Check Railway logs for mount errors
- Verify directory paths are absolute (using `.resolve()`)
- Ensure StaticFiles is imported: `from fastapi.staticfiles import StaticFiles`

