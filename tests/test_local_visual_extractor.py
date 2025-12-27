from pathlib import Path

import pytest

from api.vision.local_visual_extractor import extract_visual_elements
from api.routes.image_trust import _build_local_visual_result


def _load_sample_shot() -> bytes:
    shots = sorted(Path("api/debug_shots").glob("*.png"))
    if not shots:
        return b""
    return shots[0].read_bytes()


def test_local_visual_extractor_basic():
    data = _load_sample_shot()
    if not data:
        pytest.skip("No sample screenshot available in api/debug_shots")

    res = extract_visual_elements(data)
    assert "elements" in res
    assert isinstance(res["elements"], list)
    assert len(res["elements"]) >= 1

    result = _build_local_visual_result(data)
    assert 0 <= result.overall_score <= 100
    assert result.status in ("ok", "fallback")
    assert isinstance(result.elements, list)
    if result.status == "ok":
        assert len(result.elements) >= 1
























