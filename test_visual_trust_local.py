"""
Smoke test for local VisualTrust engine (no external services).

Usage:
    python test_visual_trust_local.py

API example:
    Invoke-RestMethod -Uri "http://127.0.0.1:8000/analyze-url" `
      -Method Post -ContentType "application/json" `
      -Body '{"url":"https://example.com"}'
"""
from __future__ import annotations

import json
from pathlib import Path

from api.local_visual_trust_engine import predict_visual_trust, get_model_status


def find_sample_image() -> Path | None:
    candidates = [
        Path(r"C:\Windows\Web\Wallpaper\Windows\img0.jpg"),
        Path("api/debug_shots/shot_20251214_201258.png"),
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def main():
    print("=" * 60)
    print("Local VisualTrust Smoke Test (HTTP endpoint)")
    print("=" * 60)
    print(f"Model status: {get_model_status()}")

    sample = find_sample_image()
    if not sample:
        print("[WARN] No sample image found; place a PNG/JPG and rerun.")
        return

    print(f"[INFO] Using sample image: {sample}")
    try:
        import requests

        files = {"file": (sample.name, sample.read_bytes(), "image/jpeg")}
        resp = requests.post("http://127.0.0.1:8000/api/analyze/image-trust-local", files=files, timeout=20)
        print(f"[HTTP] status={resp.status_code}")
        print(json.dumps(resp.json(), indent=2))
    except Exception as e:
        print(f"[ERROR] HTTP call failed: {e}")


if __name__ == "__main__":
    main()

