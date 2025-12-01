"""
Visual Trust Classifier Training Script
========================================

Trains a TensorFlow/Keras model to classify landing page hero screenshots
into three trust levels: low, medium, high.

Dataset structure:
    training_data/
      images/
        low/      (low-trust, spammy/cheap visuals)
        medium/   (mid-level, acceptable but not premium visuals)
        high/     (premium / professional visuals)

Usage:
    # Train the model
    python training/train_visual_trust_model.py

    # Predict on a single image
    python training/train_visual_trust_model.py --predict path/to/image.jpg
"""

import argparse
import os
from pathlib import Path
from typing import Dict

import numpy as np
import tensorflow as tf
from tensorflow.keras.applications import EfficientNetB0
from tensorflow.keras.applications.efficientnet import preprocess_input
from tensorflow.keras.callbacks import EarlyStopping


# ====================================================
# Configuration
# ====================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR = PROJECT_ROOT / "training_data" / "images"
MODELS_DIR = PROJECT_ROOT / "models"
MODEL_PATH = MODELS_DIR / "visual_trust_model.keras"

# Stable class mapping: low=0, medium=1, high=2
CLASS_NAMES = ["low", "medium", "high"]
CLASS_TO_INDEX = {name: idx for idx, name in enumerate(CLASS_NAMES)}

# Training parameters
IMAGE_SIZE = (224, 224)
BATCH_SIZE = 16
VALIDATION_SPLIT = 0.2
SEED = 42
EPOCHS = 15

# Global model cache for inference
_visual_trust_model = None


# ====================================================
# Dataset Loading
# ====================================================

def check_dataset_exists() -> bool:
    """Check if the dataset directory exists and has images."""
    if not DATASET_DIR.exists():
        return False

    image_exts = {".jpg", ".jpeg", ".png", ".webp"}
    for subfolder in ["low", "medium", "high"]:
        subfolder_path = DATASET_DIR / subfolder
        if subfolder_path.exists():
            for file_path in subfolder_path.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in image_exts:
                    return True
    return False


def load_datasets():
    """
    Load training and validation datasets from training_data/images/.
    
    Returns:
        train_ds: training dataset
        val_ds: validation dataset
        class_names: list of class names in the order used by the dataset
    """
    if not check_dataset_exists():
        raise RuntimeError(
            f"No images found in {DATASET_DIR}. "
            "Please add images to training_data/images/{low,medium,high}/ before training."
        )

    print(f"[INFO] Loading datasets from: {DATASET_DIR}")

    # Load training dataset
    train_ds = tf.keras.utils.image_dataset_from_directory(
        str(DATASET_DIR),
        labels="inferred",
        label_mode="int",
        image_size=IMAGE_SIZE,
        batch_size=BATCH_SIZE,
        validation_split=VALIDATION_SPLIT,
        subset="training",
        seed=SEED,
    )

    # Load validation dataset
    val_ds = tf.keras.utils.image_dataset_from_directory(
        str(DATASET_DIR),
        labels="inferred",
        label_mode="int",
        image_size=IMAGE_SIZE,
        batch_size=BATCH_SIZE,
        validation_split=VALIDATION_SPLIT,
        subset="validation",
        seed=SEED,
    )

    # Get class names from the dataset (will be sorted alphabetically)
    detected_class_names = train_ds.class_names
    print(f"[INFO] Detected class names (alphabetical order): {detected_class_names}")

    # Verify we have exactly 3 classes
    if len(detected_class_names) != 3:
        raise ValueError(
            f"Expected 3 classes (low, medium, high), but found {len(detected_class_names)}: {detected_class_names}"
        )

    # Verify all expected classes are present
    for expected_class in CLASS_NAMES:
        if expected_class not in detected_class_names:
            raise ValueError(
                f"Expected class '{expected_class}' not found in dataset. "
                f"Found classes: {detected_class_names}"
            )

    # Apply performance optimizations
    AUTOTUNE = tf.data.AUTOTUNE
    train_ds = train_ds.cache().shuffle(1000).prefetch(AUTOTUNE)
    val_ds = val_ds.cache().prefetch(AUTOTUNE)

    return train_ds, val_ds, detected_class_names


# ====================================================
# Model Building
# ====================================================

def build_model(num_classes: int = 3):
    """
    Build a Keras model with EfficientNetB0 backbone and classification head.
    
    Args:
        num_classes: Number of output classes (default: 3 for low/medium/high)
    
    Returns:
        Compiled Keras model
    """
    print("[INFO] Building model...")

    # EfficientNetB0 backbone (frozen for feature extraction)
    base_model = EfficientNetB0(
        include_top=False,
        weights="imagenet",
        input_shape=(*IMAGE_SIZE, 3),
    )
    base_model.trainable = False  # First phase: feature extractor

    # Build the full model
    inputs = tf.keras.Input(shape=(*IMAGE_SIZE, 3))
    x = preprocess_input(inputs)
    x = base_model(x, training=False)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.Dense(128, activation="relu")(x)
    x = tf.keras.layers.Dropout(0.3)(x)
    outputs = tf.keras.layers.Dense(num_classes, activation="softmax")(x)

    model = tf.keras.Model(inputs, outputs, name="visual_trust_classifier")

    # Compile the model
    model.compile(
        optimizer=tf.keras.optimizers.Adam(1e-4),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )

    model.summary()
    return model


# ====================================================
# Training
# ====================================================

def train_model():
    """Main training pipeline."""
    try:
        train_ds, val_ds, detected_class_names = load_datasets()
    except RuntimeError as e:
        print(f"[ERROR] {e}")
        return

    num_classes = len(detected_class_names)
    model = build_model(num_classes=num_classes)

    # Early stopping callback
    early_stopping = EarlyStopping(
        monitor="val_loss",
        patience=3,
        restore_best_weights=True,
        verbose=1,
    )

    print("[INFO] Starting training...")
    print(f"[INFO] Training for up to {EPOCHS} epochs with early stopping on val_loss")

    history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=EPOCHS,
        callbacks=[early_stopping],
        verbose=1,
    )

    # Print final metrics
    final_train_acc = history.history["accuracy"][-1]
    final_val_acc = history.history["val_accuracy"][-1]
    print("\n" + "=" * 60)
    print("Training Complete!")
    print(f"Final Training Accuracy: {final_train_acc:.4f}")
    print(f"Final Validation Accuracy: {final_val_acc:.4f}")
    print("=" * 60)

    # Save the model
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\n[INFO] Saving model to: {MODEL_PATH}")
    model.save(MODEL_PATH)
    print(f"[INFO] Model saved successfully to: {MODEL_PATH}")


# ====================================================
# Inference
# ====================================================

def load_visual_trust_model():
    """
    Load the trained visual trust model (cached globally).
    
    Returns:
        Loaded Keras model
    """
    global _visual_trust_model
    if _visual_trust_model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Model not found at {MODEL_PATH}. "
                "Train the model first by running: python training/train_visual_trust_model.py"
            )
        print(f"[INFO] Loading model from: {MODEL_PATH}")
        _visual_trust_model = tf.keras.models.load_model(MODEL_PATH)
        print("[INFO] Model loaded successfully.")
    return _visual_trust_model


def predict_visual_trust(image_path: str) -> Dict:
    """
    Predict visual trust level for a single image.
    
    Args:
        image_path: Path to the image file
    
    Returns:
        Dictionary with:
            - trust_label: "low" | "medium" | "high"
            - trust_scores: dict mapping class names to probabilities
    """
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")

    model = load_visual_trust_model()

    # Load and preprocess image
    img = tf.keras.utils.load_img(image_path, target_size=IMAGE_SIZE)
    img_array = tf.keras.utils.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)  # Add batch dimension
    img_array = preprocess_input(img_array)

    # Predict
    predictions = model.predict(img_array, verbose=0)
    probs = predictions[0]  # Shape: (3,)

    # Get predicted class index
    predicted_idx = int(np.argmax(probs))
    trust_label = CLASS_NAMES[predicted_idx]

    # Build trust_scores dictionary
    trust_scores = {
        CLASS_NAMES[i]: float(probs[i]) for i in range(len(CLASS_NAMES))
    }

    return {
        "trust_label": trust_label,
        "trust_scores": trust_scores,
    }


# ====================================================
# CLI
# ====================================================

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Train or run inference with the visual trust classifier."
    )
    parser.add_argument(
        "--predict",
        type=str,
        help="If provided, skips training and runs prediction on the given image path.",
    )

    args = parser.parse_args()

    if args.predict:
        # Inference mode
        try:
            result = predict_visual_trust(args.predict)
            print("\n" + "=" * 60)
            print("Visual Trust Prediction")
            print("=" * 60)
            print(f"Image: {args.predict}")
            print(f"Predicted Label: {result['trust_label']}")
            print("\nClass Probabilities:")
            for class_name, prob in result["trust_scores"].items():
                print(f"  {class_name}: {prob:.4f} ({prob*100:.2f}%)")
            print("=" * 60)
        except Exception as e:
            print(f"[ERROR] Prediction failed: {e}")
            return 1
    else:
        # Training mode
        train_model()

    return 0


if __name__ == "__main__":
    exit(main())
