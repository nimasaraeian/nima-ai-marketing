"""
Decision Signals Abstraction Layer

Shared structure for decision-critical psychological signals extracted from
multiple evidence sources (Landing Page, Ad/Banner, Pricing Page).

This module defines the unified signal structure that all evidence extractors
must populate. The signals feed into the existing Decision Brain logic.
"""

from dataclasses import dataclass
from typing import Literal, Optional, Dict, Any


@dataclass
class DecisionSignals:
    """
    Unified decision signals structure.
    
    All evidence extractors (Landing, Ad, Pricing) populate these fields.
    Signals are then merged and fed into the existing Decision State resolver.
    """
    
    # Promise & Value Clarity
    promise_strength: Literal["low", "medium", "high"]
    
    # Emotional & Psychological Tone
    emotional_tone: Literal["calm", "urgent", "aggressive", "reassuring"]
    
    # Trust & Safety
    reassurance_level: Literal["low", "medium", "high"]
    
    # Risk Perception
    risk_exposure: Literal["low", "medium", "high"]
    
    # Cognitive Load
    cognitive_load: Literal["low", "medium", "high"]
    
    # Pressure & Urgency
    pressure_level: Literal["low", "medium", "high"]
    
    # Optional: Additional context signals
    expectation_gap: Optional[Literal["low", "medium", "high"]] = None
    choice_overload: Optional[Literal["low", "medium", "high"]] = None
    transparency_level: Optional[Literal["low", "medium", "high"]] = None
    commitment_pressure: Optional[Literal["low", "medium", "high"]] = None
    
    # Metadata
    source: Optional[str] = None  # "landing", "ad", "pricing", "merged"
    confidence: Optional[float] = None  # 0.0-1.0
    signals: Optional[Dict[str, Any]] = None  # Raw signals for debugging


def create_empty_signals() -> DecisionSignals:
    """Create empty signals with default values."""
    return DecisionSignals(
        promise_strength="medium",
        emotional_tone="calm",
        reassurance_level="medium",
        risk_exposure="medium",
        cognitive_load="medium",
        pressure_level="low",
        source="empty",
        confidence=0.0
    )


def signals_to_dict(signals: DecisionSignals) -> Dict[str, Any]:
    """Convert DecisionSignals to dictionary for JSON serialization."""
    return {
        "promise_strength": signals.promise_strength,
        "emotional_tone": signals.emotional_tone,
        "reassurance_level": signals.reassurance_level,
        "risk_exposure": signals.risk_exposure,
        "cognitive_load": signals.cognitive_load,
        "pressure_level": signals.pressure_level,
        "expectation_gap": signals.expectation_gap,
        "choice_overload": signals.choice_overload,
        "transparency_level": signals.transparency_level,
        "commitment_pressure": signals.commitment_pressure,
        "source": signals.source,
        "confidence": signals.confidence,
        "signals": signals.signals
    }



