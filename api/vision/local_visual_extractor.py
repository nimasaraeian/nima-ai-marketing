"""
Lightweight local visual element extractor using OpenCV + Pillow.

Goals:
- No OpenAI / TensorFlow dependency.
- Heuristic detection of CTAs, headline region, and social proof strips.
- Basic clutter metrics to inform trust scoring.
"""
from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# Optional OpenCV for image processing
try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False
    cv2 = None
    logger.warning("opencv-python not available - visual extraction will be limited")

# Optional OCR for text extraction
try:
    import pytesseract
    HAS_OCR = True
except ImportError:
    HAS_OCR = False
    logger.warning("pytesseract not available - text extraction will be limited")


@dataclass
class DetectedElement:
    id: str
    role: str
    approx_position: str
    text: str | None
    visual_cues: List[str]
    confidence: float
    notes: str


def _resize_keep_aspect(img: np.ndarray, max_width: int = 1440) -> np.ndarray:
    h, w = img.shape[:2]
    if w <= max_width:
        return img
    scale = max_width / float(w)
    new_size = (max_width, int(h * scale))
    return cv2.resize(img, new_size, interpolation=cv2.INTER_AREA)


def _compute_edge_density(gray: np.ndarray) -> float:
    edges = cv2.Canny(gray, 100, 200)
    return float(np.count_nonzero(edges) / edges.size)


def _cta_candidates(gray: np.ndarray, hsv: np.ndarray) -> List[Tuple[int, int, int, int, float]]:
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    th = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 8)
    th = cv2.dilate(th, np.ones((3, 3), np.uint8), iterations=1)
    # Safe unpack: handle different OpenCV versions
    find_contours_result = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if isinstance(find_contours_result, tuple):
        if len(find_contours_result) == 2:
            contours, _ = find_contours_result
        elif len(find_contours_result) == 3:
            # OpenCV 3.x returns 3 values
            _, contours, _ = find_contours_result
        else:
            contours = find_contours_result[0] if len(find_contours_result) > 0 else []
    else:
        contours = find_contours_result

    h, w = gray.shape[:2]
    candidates: List[Tuple[int, int, int, int, float]] = []
    for cnt in contours:
        x, y, cw, ch = cv2.boundingRect(cnt)
        area = cw * ch
        # Relaxed thresholds: min area 200 (was 400), max 15% of image (was 12%)
        if area < 200 or area > (w * h * 0.15):
            continue
        aspect = cw / float(ch + 1e-6)
        # Relaxed aspect ratio: 1.5-10.0 (was 1.8-8.0) to catch more button shapes
        if aspect < 1.5 or aspect > 10.0:
            continue
        y_center = y + ch / 2
        # Relaxed vertical position: top 10% to bottom 90% (was 15%-80%)
        if y_center < h * 0.10 or y_center > h * 0.90:
            continue
        mask = np.zeros_like(gray)
        cv2.rectangle(mask, (x, y), (x + cw, y + ch), 255, -1)
        sat = np.mean(hsv[:, :, 1][mask == 255])
        # Relaxed saturation: min 15 (was 25) to catch more subtle colored buttons
        if sat < 15:
            continue
        x0 = max(x - int(cw * 0.15), 0)
        y0 = max(y - int(ch * 0.15), 0)
        x1 = min(x + cw + int(cw * 0.15), w)
        y1 = min(y + ch + int(ch * 0.15), h)
        patch = gray[y0:y1, x0:x1]
        inner = gray[y:y + ch, x:x + cw]
        contrast = float(abs(float(np.mean(inner)) - float(np.mean(patch))) / 255.0)
        candidates.append((x, y, cw, ch, contrast))
    candidates.sort(key=lambda c: c[4], reverse=True)
    return candidates


def _headline_region(gray: np.ndarray) -> Tuple[int, int, int, int] | None:
    h, w = gray.shape[:2]
    top = gray[: int(h * 0.35), :]
    th = cv2.adaptiveThreshold(top, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 21, 10)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 7))
    closed = cv2.morphologyEx(th, cv2.MORPH_CLOSE, kernel, iterations=2)
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    largest = max(contours, key=cv2.contourArea)
    x, y, cw, ch = cv2.boundingRect(largest)
    area = cw * ch
    if area < (w * h * 0.01):
        return None
    if cw < w * 0.25 or ch < top.shape[0] * 0.05:
        return None
    return x, y, cw, ch


def _social_proof_band(gray: np.ndarray) -> Tuple[int, int, int, int] | None:
    h, w = gray.shape[:2]
    band_top = int(h * 0.18)
    band_bottom = int(h * 0.45)
    band = gray[band_top:band_bottom, :]
    edges = cv2.Canny(band, 80, 180)
    dilated = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    smalls = 0
    xs: List[Tuple[int, int, int, int]] = []
    for c in contours:
        x, y, cw, ch = cv2.boundingRect(c)
        area = cw * ch
        if area < 60 or area > (w * h * 0.02):
            continue
        if cw > 4 * ch:
            continue
        smalls += 1
        xs.append((x, y + band_top, cw, ch))
    # Relaxed threshold: require 3+ small elements (was 5) to detect social proof band
    if smalls >= 3:
        # Safe unpack: handle variable tuple lengths
        x0 = min(item[0] if isinstance(item, (list, tuple)) and len(item) >= 1 else 0 for item in xs)
        y0 = min(item[1] if isinstance(item, (list, tuple)) and len(item) >= 2 else 0 for item in xs)
        x1 = max((item[0] + item[2]) if isinstance(item, (list, tuple)) and len(item) >= 3 else 0 for item in xs)
        y1 = max((item[1] + item[3]) if isinstance(item, (list, tuple)) and len(item) >= 4 else 0 for item in xs)
        return x0, y0, x1 - x0, y1 - y0
    return None


def _detect_ui_cta(img: np.ndarray, gray: np.ndarray, hsv: np.ndarray) -> Dict | None:
    """
    Enhanced CTA Detector: Detects buttons with solid color, border-radius, and CTA text patterns.
    """
    h, w = gray.shape[:2]
    
    # Detect rectangular regions with solid colors (low variance in HSV)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    th = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 8)
    th = cv2.dilate(th, np.ones((3, 3), np.uint8), iterations=1)
    # Safe unpack: handle different OpenCV versions
    find_contours_result = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if isinstance(find_contours_result, tuple):
        if len(find_contours_result) == 2:
            contours, _ = find_contours_result
        elif len(find_contours_result) == 3:
            # OpenCV 3.x returns 3 values
            _, contours, _ = find_contours_result
        else:
            contours = find_contours_result[0] if len(find_contours_result) > 0 else []
    else:
        contours = find_contours_result
    
    best_cta = None
    best_score = 0.0
    
    for cnt in contours:
        x, y, cw, ch = cv2.boundingRect(cnt)
        area = cw * ch
        
        # Size constraints for buttons
        if area < 500 or area > (w * h * 0.15):
            continue
        
        # Aspect ratio for buttons (wider than tall, but not too wide)
        aspect = cw / float(ch + 1e-6)
        if aspect < 1.5 or aspect > 6.0:
            continue
        
        # Check for solid color (low saturation variance in button region)
        roi_hsv = hsv[y:y+ch, x:x+cw]
        sat_variance = np.var(roi_hsv[:, :, 1])
        if sat_variance > 2000:  # Too much color variation
            continue
        
        # Score based on contrast, position, and solid color
        y_center = y + ch / 2
        position_score = 1.0 if 0.1 < (y_center / h) < 0.9 else 0.5
        
        contrast = abs(float(np.mean(gray[y:y+ch, x:x+cw])) - float(np.mean(gray[max(0,y-10):y+ch+10, max(0,x-10):x+cw+10]))) / 255.0
        
        score = (contrast * 0.4 + position_score * 0.3 + (1.0 - min(1.0, sat_variance/2000)) * 0.3)
        
        if score > best_score:
            best_score = score
            best_cta = {
                "box": (x, y, cw, ch),
                "score": score,
                "contrast": contrast
            }
    
    if best_cta and best_score > 0.5:
        x, y, cw, ch = best_cta["box"]
        pos = _approx_position((x, y, cw, ch), h, w)
        return {
            "id": "primary_cta",
            "role": "cta",
            "approx_position": pos,
            "confidence": min(0.95, 0.6 + best_score * 0.2)
        }
    return None


def _detect_dashboard_metrics(img: np.ndarray, gray: np.ndarray) -> Dict | None:
    """
    Dashboard/Metrics Detector: Detects large numbers, currency symbols, and chart-like patterns.
    """
    h, w = gray.shape[:2]
    
    # Look for regions with high density of horizontal/vertical lines (chart axes)
    edges = cv2.Canny(gray, 50, 150)
    
    # Detect horizontal lines (chart axes)
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    horizontal_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, horizontal_kernel)
    
    # Detect vertical lines
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
    vertical_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, vertical_kernel)
    
    # Combine to find chart-like regions
    chart_mask = cv2.bitwise_or(horizontal_lines, vertical_lines)
    contours, _ = cv2.findContours(chart_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    for cnt in contours:
        x, y, cw, ch = cv2.boundingRect(cnt)
        area = cw * ch
        
        # Charts are typically medium to large regions
        if area < (w * h * 0.05) or area > (w * h * 0.4):
            continue
        
        # Check for high line density (indicating axes/grid)
        roi_edges = edges[y:y+ch, x:x+cw]
        line_density = np.count_nonzero(roi_edges) / roi_edges.size if roi_edges.size > 0 else 0
        
        if line_density > 0.15:  # High line density suggests chart
            pos = _approx_position((x, y, cw, ch), h, w)
            return {
                "id": "metrics_dashboard",
                "role": "social_proof",
                "approx_position": pos,
                "confidence": 0.75
            }
    
    return None


def _detect_ui_form(img: np.ndarray, gray: np.ndarray) -> Dict | None:
    """
    UI Form Detector: Detects input fields, labels, and form-like structures.
    """
    h, w = gray.shape[:2]
    
    # Forms typically have multiple rectangular regions (input fields)
    # Look for repeated rectangular patterns
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    th = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
    
    # Find rectangular contours (potential input fields)
    # Safe unpack: handle different OpenCV versions
    find_contours_result = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if isinstance(find_contours_result, tuple):
        if len(find_contours_result) == 2:
            contours, _ = find_contours_result
        elif len(find_contours_result) == 3:
            # OpenCV 3.x returns 3 values
            _, contours, _ = find_contours_result
        else:
            contours = find_contours_result[0] if len(find_contours_result) > 0 else []
    else:
        contours = find_contours_result
    
    form_boxes = []
    for cnt in contours:
        x, y, cw, ch = cv2.boundingRect(cnt)
        area = cw * ch
        
        # Input fields are typically medium-sized rectangles
        if area < 800 or area > (w * h * 0.1):
            continue
        
        # Input fields are usually wider than tall
        aspect = cw / float(ch + 1e-6)
        if aspect < 2.0 or aspect > 8.0:
            continue
        
        # Check if it looks like an input (hollow center or border-like)
        roi = gray[y:y+ch, x:x+cw]
        center_region = roi[int(ch*0.2):int(ch*0.8), int(cw*0.2):int(cw*0.8)]
        border_region = np.concatenate([
            roi[0:int(ch*0.2), :].flatten(),
            roi[int(ch*0.8):, :].flatten(),
            roi[:, 0:int(cw*0.2)].flatten(),
            roi[:, int(cw*0.8):].flatten()
        ])
        
        if center_region.size > 0 and border_region.size > 0:
            center_mean = np.mean(center_region)
            border_mean = np.mean(border_region)
            # Input fields often have different center vs border (hollow or filled)
            if abs(center_mean - border_mean) > 30:
                form_boxes.append((x, y, cw, ch))
    
    # If we found multiple form-like boxes in a region, it's likely a form
    if len(form_boxes) >= 2:
        # Group nearby boxes - safe unpack
        x0 = min(item[0] if isinstance(item, (list, tuple)) and len(item) >= 1 else 0 for item in form_boxes)
        y0 = min(item[1] if isinstance(item, (list, tuple)) and len(item) >= 2 else 0 for item in form_boxes)
        x1 = max((item[0] + item[2]) if isinstance(item, (list, tuple)) and len(item) >= 3 else 0 for item in form_boxes)
        y1 = max((item[1] + item[3]) if isinstance(item, (list, tuple)) and len(item) >= 4 else 0 for item in form_boxes)
        
        form_area = (x1 - x0) * (y1 - y0)
        if form_area > (w * h * 0.1):  # Forms are typically substantial
            pos = _approx_position((x0, y0, x1-x0, y1-y0), h, w)
            return {
                "id": "payment_form",
                "role": "risk_reduction",
                "approx_position": pos,
                "confidence": min(0.95, 0.7 + len(form_boxes) * 0.05)
            }
    
    return None


def _detect_branding_authority(img: np.ndarray, gray: np.ndarray) -> Dict | None:
    """
    Branding/Authority Detector: Detects logo in header and consistent UI theme.
    """
    h, w = gray.shape[:2]
    
    # Check top 20% of image for logo-like regions (header area)
    header_region = gray[:int(h * 0.2), :]
    
    # Look for compact, square-ish regions in header (typical logo shape)
    edges = cv2.Canny(header_region, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    for cnt in contours:
        x, y, cw, ch = cv2.boundingRect(cnt)
        area = cw * ch
        
        # Logos are typically small to medium, compact regions
        if area < 200 or area > (w * h * 0.05):
            continue
        
        # Logos are often roughly square or slightly rectangular
        aspect = cw / float(ch + 1e-6)
        if aspect < 0.5 or aspect > 2.5:
            continue
        
        # Check for consistent color/theme in header (branding indicator)
        header_hsv = cv2.cvtColor(img[:int(h * 0.2), :], cv2.COLOR_BGR2HSV)
        hue_variance = np.var(header_hsv[:, :, 0])
        
        # Low hue variance suggests consistent branding
        if hue_variance < 500:  # Consistent color theme
            pos = _approx_position((x, y, cw, ch), h, w)
            return {
                "id": "brand_authority",
                "role": "trust_signal",
                "approx_position": pos,
                "confidence": 0.8
            }
    
    return None


def _approx_position(box: Tuple[int, int, int, int], h: int, w: int) -> str:
    x, y, bw, bh = box
    cx = x + bw / 2
    cy = y + bh / 2
    horiz = "left" if cx < w * (1 / 3) else "right" if cx > w * (2 / 3) else "center"
    vert = "top" if cy < h * (1 / 3) else "bottom" if cy > h * (2 / 3) else "middle"
    return f"{vert}-{horiz}"


def _extract_text_from_region(img: Image.Image, box: Tuple[int, int, int, int]) -> str | None:
    """Extract text from a specific region using OCR if available."""
    if not HAS_OCR:
        return None
    try:
        x, y, w, h = box
        # Crop the region
        region = img.crop((x, y, x + w, y + h))
        # Extract text
        text = pytesseract.image_to_string(region, config='--psm 7').strip()
        return text if text else None
    except Exception as e:
        logger.debug("OCR failed for region %s: %s", box, e)
        return None


def _extract_color_palette(img: np.ndarray, box: Tuple[int, int, int, int] | None = None) -> Dict[str, Any]:
    """Extract dominant colors from image or region."""
    try:
        if box:
            x, y, w, h = box
            region = img[y:y+h, x:x+w]
        else:
            region = img
        
        # Resize for faster processing
        small = cv2.resize(region, (100, 100))
        pixels = small.reshape(-1, 3)
        
        # Convert to RGB
        pixels_rgb = cv2.cvtColor(small.reshape(1, -1, 3), cv2.COLOR_BGR2RGB).reshape(-1, 3)
        
        # Get dominant colors using K-means (if sklearn available)
        try:
            from sklearn.cluster import KMeans
            kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
            kmeans.fit(pixels_rgb)
            colors = kmeans.cluster_centers_.astype(int)
            labels = kmeans.labels_
            counts = np.bincount(labels)
            
            # Sort by frequency
            sorted_indices = np.argsort(counts)[::-1]
            dominant_colors = []
            for idx in sorted_indices[:3]:  # Top 3 colors
                r, g, b = colors[idx]
                dominant_colors.append({
                    "rgb": [int(r), int(g), int(b)],
                    "hex": f"#{r:02x}{g:02x}{b:02x}",
                    "frequency": float(counts[idx] / len(labels))
                })
            
            return {"dominant_colors": dominant_colors}
        except ImportError:
            # Fallback if sklearn not available - use simple histogram approach
        small = cv2.resize(region, (50, 50))
        pixels = small.reshape(-1, 3)
        pixels_rgb = cv2.cvtColor(small.reshape(1, -1, 3), cv2.COLOR_BGR2RGB).reshape(-1, 3)
        
        # Simple histogram-based approach
        hist_r = np.histogram(pixels_rgb[:, 0], bins=10)[0]
        hist_g = np.histogram(pixels_rgb[:, 1], bins=10)[0]
        hist_b = np.histogram(pixels_rgb[:, 2], bins=10)[0]
        
        dominant_r = int(np.argmax(hist_r) * 25.5)
        dominant_g = int(np.argmax(hist_g) * 25.5)
        dominant_b = int(np.argmax(hist_b) * 25.5)
        
        return {
            "dominant_colors": [{
                "rgb": [dominant_r, dominant_g, dominant_b],
                "hex": f"#{dominant_r:02x}{dominant_g:02x}{dominant_b:02x}",
                "frequency": 1.0
            }]
        }
    except Exception as e:
        logger.debug("Color extraction failed: %s", e)
        return {"dominant_colors": []}


def _detect_logos_enhanced(img: np.ndarray, gray: np.ndarray) -> List[Dict[str, Any]]:
    """Enhanced logo detection using contour analysis and shape matching."""
    logos = []
    h, w = gray.shape[:2]
    
    # Detect small square/rectangular regions (typical logo shapes)
    edges = cv2.Canny(gray, 50, 150)
    dilated = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)
    find_contours_result = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if isinstance(find_contours_result, tuple):
        if len(find_contours_result) == 2:
            contours, _ = find_contours_result
        elif len(find_contours_result) == 3:
            _, contours, _ = find_contours_result
        else:
            contours = find_contours_result[0] if len(find_contours_result) > 0 else []
    else:
        contours = find_contours_result
    
    for cnt in contours:
        x, y, cw, ch = cv2.boundingRect(cnt)
        area = cw * ch
        
        # Logo size constraints
        if area < 100 or area > (w * h * 0.05):
            continue
        
        # Aspect ratio for logos (usually square-ish or slightly rectangular)
        aspect = cw / float(ch + 1e-6)
        if aspect < 0.5 or aspect > 2.0:
            continue
        
        # Check if in top region (where logos usually are)
        y_center = y + ch / 2
        if y_center > h * 0.3:  # Only top 30% of page
            continue
        
        # Extract color from region
        color_info = _extract_color_palette(img, (x, y, cw, ch))
        
        # Safety check: ensure color_info is always a dict (fail-safe)
        safe_color_info = color_info or {}
        
        logos.append({
            "box": (x, y, cw, ch),
            "position": _approx_position((x, y, cw, ch), h, w),
            "colors": safe_color_info.get("dominant_colors", []),
            "confidence": 0.6
        })
    
    return logos[:5]  # Return top 5 logo candidates


def _draw_box(img: np.ndarray, box: Tuple[int, int, int, int], color: Tuple[int, int, int], label: str) -> None:
    x, y, bw, bh = box
    cv2.rectangle(img, (x, y), (x + bw, y + bh), color, 2)
    text_y = y - 6 if y - 6 > 10 else y + bh + 15
    cv2.putText(img, label, (x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)


def extract_visual_elements(image_bytes: bytes, debug: bool = False) -> Dict:
    """
    Extract heuristic visual elements and metrics from an image.
    """
    if not image_bytes:
        return {"elements": [], "metrics": {}}

    # Fallback if OpenCV is not available
    if not HAS_OPENCV:
        logger.warning("OpenCV not available - returning minimal visual extraction")
        try:
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            w, h = img.size
            return {
                "elements": [],
                "metrics": {
                    "edge_density": 0.0,
                    "text_block_density": 0.0,
                    "cta_candidates": 0,
                    "overall_color_palette": [],
                    "detected_logos_count": 0,
                },
                "analysisStatus": "fallback",
                "error": "opencv_not_available"
            }
        except Exception:
            return {"elements": [], "metrics": {}}

    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception:
        return {"elements": [], "metrics": {}}

    np_img = np.array(img)[:, :, ::-1]  # RGB -> BGR for OpenCV
    np_img = _resize_keep_aspect(np_img, max_width=1440)
    hsv = cv2.cvtColor(np_img, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(np_img, cv2.COLOR_BGR2GRAY)
    overlay = np_img.copy() if debug else None

    edge_density = _compute_edge_density(gray)

    cta_boxes = _cta_candidates(gray, hsv)
    headline_box = _headline_region(gray)
    social_box = _social_proof_band(gray)

    # UI-aware detectors
    ui_cta = _detect_ui_cta(np_img, gray, hsv)
    dashboard_metrics = _detect_dashboard_metrics(np_img, gray)
    ui_form = _detect_ui_form(np_img, gray)
    branding_authority = _detect_branding_authority(np_img, gray)

    text_like_mask = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 19, 10)
    text_like_mask = cv2.dilate(text_like_mask, np.ones((3, 3), np.uint8), iterations=1)
    text_blocks = np.count_nonzero(text_like_mask) / text_like_mask.size

    elements: List[Dict] = []
    h, w = gray.shape[:2]
    final_boxes: List[Tuple[str, Tuple[int, int, int, int], float | None]] = []

    # Log candidate thresholds and areas for visibility during debugging
    # Safe unpack: handle variable tuple lengths
    cta_candidate_details = []
    for item in cta_boxes:
        if isinstance(item, (list, tuple)) and len(item) >= 5:
            x, y, cw, ch, contrast = item[0], item[1], item[2], item[3], item[4]
            cta_candidate_details.append({"box": (x, y, cw, ch), "area": int(cw * ch), "contrast": float(contrast)})
        elif isinstance(item, (list, tuple)) and len(item) >= 4:
            # Fallback: if only 4 values, assume no contrast
            x, y, cw, ch = item[0], item[1], item[2], item[3]
            cta_candidate_details.append({"box": (x, y, cw, ch), "area": int(cw * ch), "contrast": 0.5})
    max_area = w * h * 0.12
    logger.info(
        "CTA candidates=%d areas=%s thresholds area=[%d, %d] aspect=[%.1f, %.1f] y_center=[%.2f, %.2f] min_sat=%d",
        len(cta_boxes),
        [c["area"] for c in cta_candidate_details],
        200,
        int(max_area),
        1.5,
        10.0,
        0.10,
        0.90,
        15,
    )
    if cta_candidate_details:
        logger.debug("CTA candidate detail: %s", cta_candidate_details)

    # Extract overall color palette
    overall_colors = _extract_color_palette(np_img)
    
    # Detect logos
    detected_logos = _detect_logos_enhanced(np_img, gray)
    
    if headline_box:
        pos = _approx_position(headline_box, h, w)
        x, y, cw, ch = headline_box
        # Extract text from headline region
        headline_text = _extract_text_from_region(img, headline_box) if HAS_OCR else None
        # Extract colors from headline region
        headline_colors = _extract_color_palette(np_img, headline_box)
        elements.append(
            {
                "id": "hero_region",
                "role": "headline",
                "approx_position": pos,
                "coordinates": {"x": int(x), "y": int(y), "width": int(cw), "height": int(ch)},
                "text": headline_text,
                "colors": headline_colors.get("dominant_colors", []),
                "visual_cues": ["large-text-region"],
                "analysis": {"confidence": 0.65, "notes": "Detected prominent top-region text cluster."},
            }
        )
        final_boxes.append(("headline", headline_box, None))

    # Safe unpack: handle variable tuple lengths
    for idx, item in enumerate(cta_boxes[:2], start=1):
        if isinstance(item, (list, tuple)) and len(item) >= 5:
            x, y, cw, ch, contrast = item[0], item[1], item[2], item[3], item[4]
        elif isinstance(item, (list, tuple)) and len(item) >= 4:
            # Fallback: if only 4 values, assume no contrast
            x, y, cw, ch = item[0], item[1], item[2], item[3]
            contrast = 0.5
        else:
            logger.warning(f"Invalid cta_box item at index {idx}: {item}, skipping")
            continue
        pos = _approx_position((x, y, cw, ch), h, w)
        # Extract text from CTA region
        cta_text = _extract_text_from_region(img, (x, y, cw, ch)) if HAS_OCR else None
        # Extract colors from CTA region
        cta_colors = _extract_color_palette(np_img, (x, y, cw, ch))
        elements.append(
            {
                "id": f"primary_cta_{idx}",
                "role": "cta",
                "approx_position": pos,
                "coordinates": {"x": int(x), "y": int(y), "width": int(cw), "height": int(ch)},
                "text": cta_text,
                "colors": cta_colors.get("dominant_colors", []),
                "visual_cues": ["button-like", "high-contrast", "rectangular"],
                "analysis": {"confidence": min(1.0, 0.5 + contrast), "notes": "CTA candidate by shape/contrast."},
            }
        )
        final_boxes.append((f"cta_{idx}", (x, y, cw, ch), contrast))

    if social_box:
        pos = _approx_position(social_box, h, w)
        x, y, cw, ch = social_box
        social_colors = _extract_color_palette(np_img, social_box)
        elements.append(
            {
                "id": "social_proof_strip",
                "role": "logos",
                "approx_position": pos,
                "coordinates": {"x": int(x), "y": int(y), "width": int(cw), "height": int(ch)},
                "text": None,
                "colors": social_colors.get("dominant_colors", []),
                "visual_cues": ["multiple small marks in row"],
                "analysis": {"confidence": 0.55, "notes": "Horizontal band with multiple small components."},
            }
        )
        final_boxes.append(("social_proof", social_box, None))
    
    # Add detected logos as separate elements
    for idx, logo in enumerate(detected_logos, start=1):
        x, y, cw, ch = logo["box"]
        elements.append({
            "id": f"logo_{idx}",
            "role": "logo",
            "approx_position": logo["position"],
            "coordinates": {"x": int(x), "y": int(y), "width": int(cw), "height": int(ch)},
            "text": None,
            "colors": logo.get("colors", []),
            "visual_cues": ["logo", "branding"],
            "analysis": {"confidence": logo["confidence"], "notes": "Detected logo candidate."},
        })

    # Add UI-aware detected elements with enhanced info
    if ui_cta:
        # Extract box from ui_cta if available
        ui_cta_box = ui_cta.get("box")
        if ui_cta_box:
            x, y, cw, ch = ui_cta_box
            ui_cta_text = _extract_text_from_region(img, ui_cta_box) if HAS_OCR else None
            ui_cta_colors = _extract_color_palette(np_img, ui_cta_box)
        else:
            ui_cta_text = None
            ui_cta_colors = {"dominant_colors": []}
            x, y, cw, ch = 0, 0, 0, 0
        elements.append({
            "id": ui_cta["id"],
            "role": ui_cta["role"],
            "approx_position": ui_cta["approx_position"],
            "coordinates": {"x": int(x), "y": int(y), "width": int(cw), "height": int(ch)} if ui_cta_box else None,
            "text": ui_cta_text,
            "colors": ui_cta_colors.get("dominant_colors", []),
            "visual_cues": ["solid-color", "button-like", "border-radius"],
            "analysis": {"confidence": ui_cta["confidence"], "notes": "UI-aware CTA detection with solid color and rounded corners."},
        })
    
    if dashboard_metrics:
        dashboard_box = dashboard_metrics.get("box")
        if dashboard_box:
            x, y, cw, ch = dashboard_box
            dashboard_colors = _extract_color_palette(np_img, dashboard_box)
        else:
            dashboard_colors = {"dominant_colors": []}
            x, y, cw, ch = 0, 0, 0, 0
        elements.append({
            "id": dashboard_metrics["id"],
            "role": dashboard_metrics["role"],
            "approx_position": dashboard_metrics["approx_position"],
            "coordinates": {"x": int(x), "y": int(y), "width": int(cw), "height": int(ch)} if dashboard_box else None,
            "text": None,
            "colors": dashboard_colors.get("dominant_colors", []),
            "visual_cues": ["chart-axes", "metrics-display"],
            "analysis": {"confidence": dashboard_metrics["confidence"], "notes": "Dashboard/metrics region with chart-like patterns."},
        })
    
    if ui_form:
        form_box = ui_form.get("box")
        if form_box:
            x, y, cw, ch = form_box
            form_colors = _extract_color_palette(np_img, form_box)
        else:
            form_colors = {"dominant_colors": []}
            x, y, cw, ch = 0, 0, 0, 0
        elements.append({
            "id": ui_form["id"],
            "role": ui_form["role"],
            "approx_position": ui_form["approx_position"],
            "coordinates": {"x": int(x), "y": int(y), "width": int(cw), "height": int(ch)} if form_box else None,
            "text": None,
            "colors": form_colors.get("dominant_colors", []),
            "visual_cues": ["input-fields", "form-structure"],
            "analysis": {"confidence": ui_form["confidence"], "notes": "UI form detected with multiple input fields."},
        })
    
    if branding_authority:
        brand_box = branding_authority.get("box")
        if brand_box:
            x, y, cw, ch = brand_box
            brand_colors = _extract_color_palette(np_img, brand_box)
        else:
            brand_colors = {"dominant_colors": []}
            x, y, cw, ch = 0, 0, 0, 0
        elements.append({
            "id": branding_authority["id"],
            "role": branding_authority["role"],
            "approx_position": branding_authority["approx_position"],
            "coordinates": {"x": int(x), "y": int(y), "width": int(cw), "height": int(ch)} if brand_box else None,
            "text": None,
            "colors": brand_colors.get("dominant_colors", []),
            "visual_cues": ["logo", "consistent-theme"],
            "analysis": {"confidence": branding_authority["confidence"], "notes": "Branding/authority signal with logo and consistent UI theme."},
        })

    metrics = {
        "edge_density": float(edge_density),
        "text_block_density": float(text_blocks),
        "cta_candidates": len(cta_boxes),
        "overall_color_palette": overall_colors.get("dominant_colors", []),
        "detected_logos_count": len(detected_logos),
    }

    debug_info = None
    if debug and overlay is not None:
        debug_info = {
            "overlayPath": None,
            "candidateCount": len(cta_boxes),
            "finalCount": len(final_boxes),
        }
        # Draw candidate boxes (all) in orange
        for idx, detail in enumerate(cta_candidate_details, start=1):
            _draw_box(overlay, detail["box"], (0, 165, 255), f"CTA cand {idx} c={detail['contrast']:.2f}")
        # Draw final boxes on top with distinct colors
        for label, box, confidence in final_boxes:
            color = (0, 200, 0) if "cta" in label else (255, 0, 0) if label == "headline" else (255, 0, 255)
            caption = f"{label}"
            if confidence is not None:
                caption = f"{caption} c={confidence:.2f}"
            _draw_box(overlay, box, color, caption)

        try:
            from api.core.config import get_debug_shots_dir
            debug_dir = get_debug_shots_dir()  # Use shared config
            ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
            overlay_path = debug_dir / f"overlay_{ts}.png"
            written = cv2.imwrite(str(overlay_path), overlay)
            if written:
                debug_info["overlayPath"] = str(overlay_path)
            else:
                logger.warning("cv2.imwrite reported failure for overlay path: %s", overlay_path)
        except Exception as exc:
            logger.exception("Failed to write debug overlay: %s", exc)

    # Check if we have sufficient UI understanding
    if len(elements) < 4:
        result = {
            "elements": elements,
            "metrics": metrics,
            "analysisStatus": "fallback",
            "error": "vision_model_insufficient_ui_understanding"
        }
    else:
        result = {"elements": elements, "metrics": metrics}
    
    if debug_info:
        result["debug"] = debug_info
    return result

