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
"""
    
    # Cache it
    _cached_system_prompt = system_prompt
    
    return system_prompt


def clear_cache():
    """Clear the cached system prompt (useful for development/reloading)"""
    global _cached_system_prompt
    _cached_system_prompt = None

