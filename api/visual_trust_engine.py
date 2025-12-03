"""
Visual Trust Engine
===================

Runtime helper for loading and using the trained visual trust model.

Responsibilities:
- Load the trained TensorFlow/Keras model once at import time
- Load the class name mapping used during training
- Provide a simple interface:

    analyze_visual_trust_from_path(image_path: str) -> dict

Which returns:
    {
        "trust_label": "high_trust" | "medium_trust" | "low_trust",
        "trust_scores": {...},          # per-class probabilities
        "trust_score_numeric": float,   # mapped numeric score (e.g. 80/50/20)
        "visual_comment": str           # short textual interpretation
    }
"""

import logging
import os
import sys
from pathlib import Path
from typing import Dict, List

import numpy as np

try:
    import tensorflow as tf  # type: ignore
except ModuleNotFoundError as exc:  # pragma: no cover - environment specific
    tf = None  # type: ignore
    _TF_IMPORT_ERROR = exc
else:
    _TF_IMPORT_ERROR = None


# Ensure project root is on sys.path so we can import training modules if needed
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

MODELS_DIR = PROJECT_ROOT / "models"
MODEL_PATH = MODELS_DIR / "visual_trust_model.keras"
CLASS_NAMES_PATH = MODELS_DIR / "visual_trust_class_names.txt"

# Global caches so we don't reload on every request
_MODEL: "tf.keras.Model | None" = None
_CLASS_NAMES: List[str] | None = None
_PREPROCESS_FN = None
TF_AVAILABLE = _TF_IMPORT_ERROR is None
LOGGER = logging.getLogger("visual_trust_engine")
TF_WARNING = (
    "TensorFlow is not installed. Visual trust scoring is disabled. "
    "Install tensorflow>=2.15 and set PYTHON_VERSION=3.12 on Render to enable this feature."
)


def _ensure_tensorflow() -> None:
    """
    Guard helper to raise a descriptive error when TensorFlow is missing.
    """
    if not TF_AVAILABLE:
        raise RuntimeError(TF_WARNING) from _TF_IMPORT_ERROR


def _load_class_names() -> List[str]:
    """
    Load class names from the text file created during training.
    Falls back to inferring from dataset/images subfolders if needed.
    """
    global _CLASS_NAMES
    if _CLASS_NAMES is not None:
        return _CLASS_NAMES

    if CLASS_NAMES_PATH.exists():
        with CLASS_NAMES_PATH.open("r", encoding="utf-8") as f:
            names = [line.strip() for line in f if line.strip()]
            if names:
                _CLASS_NAMES = names
                return _CLASS_NAMES

    # Fallback: infer from dataset directory (kept in sync with training script)
    dataset_dir = PROJECT_ROOT / "dataset" / "images"
    if dataset_dir.exists():
        subdirs = sorted(
            [
                d.name
                for d in dataset_dir.iterdir()
                if d.is_dir() and not d.name.startswith(".")
            ]
        )
        if subdirs:
            _CLASS_NAMES = subdirs
            return _CLASS_NAMES

    raise RuntimeError(
        "Could not determine visual trust class names. "
        "Train the model first with training/train_visual_trust_model.py."
    )


def _get_preprocess_fn():
    """
    Return the preprocessing function matching the backbone (EfficientNetB0).
    Cached after first import.
    """
    _ensure_tensorflow()
    global _PREPROCESS_FN
    if _PREPROCESS_FN is None:
        from tensorflow.keras.applications.efficientnet import preprocess_input

        _PREPROCESS_FN = preprocess_input
    return _PREPROCESS_FN


def _load_model() -> tf.keras.Model:
    """
    Load the trained Keras model once and cache it in memory.
    """
    _ensure_tensorflow()
    global _MODEL
    if _MODEL is not None:
        return _MODEL

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Visual trust model not found at {MODEL_PATH}. "
            "Train it first with: python training/train_visual_trust_model.py"
        )

    print(f"[VISUAL_TRUST_ENGINE] Loading model from {MODEL_PATH} ...")
    _MODEL = tf.keras.models.load_model(MODEL_PATH)
    print("[VISUAL_TRUST_ENGINE] Model loaded and cached in memory.")
    return _MODEL


def _map_label_to_numeric(trust_label: str) -> float:
    """
    Map a discrete trust label to a simple numeric score.
    Defaults can be adjusted later.
    """
    mapping: Dict[str, float] = {
        "high_trust": 80.0,
        "medium_trust": 50.0,
        "low_trust": 20.0,
    }
    return mapping.get(trust_label, 50.0)


def _build_visual_comment(trust_label: str) -> str:
    """
    Simple rule-based description for the visual trust level.
    """
    label = (trust_label or "").lower()
    if "high" in label:
        return "The visual design looks professional and trustworthy for a cold audience."
    if "medium" in label:
        return "The visual design is mixed; some elements support trust, others may confuse users."
    if "low" in label:
        return "The visual design looks low-trust or spammy and may reduce conversion for cold traffic."
    return "Visual trust level is unclear. Use this only as a rough signal, not a final decision."


def analyze_visual_trust_from_path(image_path: str) -> Dict:
    """
    Analyze visual trust from an image file path.

    Returns:
        {
            "trust_label": "high_trust" | "medium_trust" | "low_trust",
            "trust_scores": {...},          # per-class probabilities
            "trust_score_numeric": float    # mapped numeric score (e.g. 80/50/20)
        }
    """
    image_path = str(image_path)
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"Image file not found for visual trust analysis: {image_path}")

    if not TF_AVAILABLE:
        LOGGER.warning("%s", TF_WARNING)
        trust_label = "medium_trust"
        fallback_scores = {
            "high_trust": 0.34,
            "medium_trust": 0.33,
            "low_trust": 0.33,
        }

        return {
            "trust_label": trust_label,
            "trust_scores": fallback_scores,
            "trust_score_numeric": _map_label_to_numeric(trust_label),
            "visual_comment": (
                "TensorFlow is missing on the server, returning a neutral trust estimate. "
                "Deploy with tensorflow installed to enable the trained model."
            ),
        }

    model = _load_model()
    class_names = _load_class_names()
    preprocess_fn = _get_preprocess_fn()

    # The training script uses IMAGE_SIZE = (224, 224)
    target_size = (224, 224)

    # Load and preprocess image
    img = tf.keras.utils.load_img(image_path, target_size=target_size)
    img_array = tf.keras.utils.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)  # shape (1, H, W, 3)
    img_array = preprocess_fn(img_array)

    # Predict probabilities
    preds = model.predict(img_array)
    probs = preds[0]  # (num_classes,)

    idx_to_label = {idx: name for idx, name in enumerate(class_names)}
    top_idx = int(np.argmax(probs))
    trust_label = idx_to_label[top_idx]

    trust_scores = {
        idx_to_label[i]: float(probs[i]) for i in range(len(class_names))
    }

    numeric_score = _map_label_to_numeric(trust_label)
    visual_comment = _build_visual_comment(trust_label)

    return {
        "trust_label": trust_label,
        "trust_scores": trust_scores,
        "trust_score_numeric": numeric_score,
        "visual_comment": visual_comment,
    }


# Backwards compatibility alias (older code may still import this name)
def analyze_visual_trust_from_file(file_path: str) -> Dict:
    return analyze_visual_trust_from_path(file_path)


