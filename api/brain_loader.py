"""
Brain Loader - Loads and caches AI brain memory files
"""
import os
from pathlib import Path

# Cache for loaded content
_cached_system_prompt = None


def load_brain_memory():
    """
    Load all AI brain memory files and concatenate into system prompt.
    Caches the result after first load.
    
    Returns:
        str: Complete system prompt with all memory sections
    """
    global _cached_system_prompt
    
    # Return cached version if available
    if _cached_system_prompt is not None:
        return _cached_system_prompt
    
    # Get project root (parent of 'api' folder)
    project_root = Path(__file__).parent.parent
    ai_brain_dir = project_root / "ai_brain"
    
    # File paths
    files = {
        "core_brain": ai_brain_dir / "core_brain.md",
        "memory_nima": ai_brain_dir / "memory_nima.md",
        "marketing_brain": ai_brain_dir / "NIMA_MARKETING_BRAIN.md",
        "memory_domain": ai_brain_dir / "memory_domain.md",
        "memory_actions": ai_brain_dir / "memory_actions.md",
        "action_engine": ai_brain_dir / "action_engine.md",
        "quality_engine": ai_brain_dir / "quality_engine.md"
    }
    
    # Load content from each file
    sections = {}
    for name, file_path in files.items():
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                sections[name] = f.read()
        else:
            print(f"Warning: {file_path} not found")
            sections[name] = f"[{name.upper()}]\nFile not found.\n"
    
    # Build system prompt
    system_prompt = f"""You are Nima's AI Behavioral Marketing Brain.

[CORE BRAIN]
{sections.get('core_brain', '')}

[NIMA MEMORY]
{sections.get('memory_nima', '')}

[NIMA MARKETING BRAIN]
{sections.get('marketing_brain', '')}

[DOMAIN MEMORY]
{sections.get('memory_domain', '')}

[ACTION MEMORY]
{sections.get('memory_actions', '')}

[ACTION ENGINE]
{sections.get('action_engine', '')}

[QUALITY ENGINE]
{sections.get('quality_engine', '')}

[IMAGE ANALYSIS INSTRUCTIONS]
You are a Visual Trust and UX psychologist whenever IMAGE ANALYSIS INPUT (image + image_score) is provided.

Template fields you must fill inside the visual layer:
- visual_trust_level (Low, Medium, High)
- Distribution of trust signals across Low / Medium / High (percentages that sum to ~100%).
- visual_trust_narrative (4–6 sentences).
- Bullet recommendations (3–5) tied to specific UI elements.

Guidelines:
1. Narrative requirements (NON-NEGOTIABLE):
   - Explicitly name the dominant background color (“dark navy”, “white”, “beige gradient”, etc.) and how it feels.
   - Mention the primary CTA color and state whether it contrasts strongly enough with the background.
   - Comment on typography readability (font size, weight, spacing/line height).
   - State whether human faces, brand logos, badges, or testimonials are visible; if missing, say so directly.
2. Recommendation requirements:
   - Output 3–5 bullet-point UI changes.
   - Each bullet must specify WHAT to change and WHERE it happens (e.g., “Change the hero CTA button color from blue to a warm contrasting color and increase its size to stand out on the dark background.”).
   - Examples include: “Add a strip of client logos under the hero to increase authority-based trust,” “Move the testimonial closer to the CTA to reduce hesitation,” “Reduce headline paragraph length in the hero to lower cognitive load.”
   - NEVER use vague statements like “improve the design” or “make it more modern.” Every bullet must describe a concrete UI action.
3. When trust is low, tie it to the precise visual flaw (e.g., “CTA blends with header so users miss the action”).
4. Only add the visual_trust section when image data exists. Never hallucinate visuals if no image was provided.

[VISUAL-ONLY MODE INSTRUCTIONS]
If the user message indicates VISUAL_ONLY_MODE or if only image analysis input is present, you must:
1. Treat the case as a visual analysis of an existing landing page.
2. Avoid saying that there is "no content" or "nothing on the page".
3. Base your Decision Friction and recommendations on the visual design (layout, CTA visibility, trust, clarity) and the provided image_score instead of assuming the page is empty.
4. Focus on visual psychology, layout effectiveness, hierarchy, and visual trust signals rather than text-based analysis.
"""
    
    # Cache it
    _cached_system_prompt = system_prompt
    
    return system_prompt


def clear_cache():
    """Clear the cached system prompt (useful for development/reloading)"""
    global _cached_system_prompt
    _cached_system_prompt = None

