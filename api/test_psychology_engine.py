"""
Test script for the CORE PSYCHOLOGY ENGINE

Tests the 13-pillar psychology analysis system.
"""

import json
from psychology_engine import (
    analyze_psychology,
    PsychologyAnalysisInput
)

def test_psychology_analysis():
    """Test the psychology analysis with sample content"""
    
    # Sample marketing copy to test
    sample_text = """
    Transform Your Business with AI-Powered Marketing
    
    Are you struggling to get results from your marketing campaigns? 
    Our revolutionary AI platform helps you create high-converting ads 
    that drive real revenue. Join thousands of successful businesses 
    who have already transformed their marketing.
    
    Get started today and see results in 30 days or your money back!
    """
    
    # Create input
    input_data = PsychologyAnalysisInput(
        raw_text=sample_text,
        platform="landing_page",
        goal=["leads", "sales"],
        audience="cold",
        language="en"
    )
    
    print("=" * 80)
    print("TESTING CORE PSYCHOLOGY ENGINE")
    print("=" * 80)
    print(f"\nInput Text:\n{sample_text}\n")
    print("=" * 80)
    print("\nAnalyzing...\n")
    
    try:
        # Run analysis
        result = analyze_psychology(input_data)
        
        # Display results
        print("=" * 80)
        print("ANALYSIS RESULTS")
        print("=" * 80)
        
        # Overall summary
        overall = result.overall
        print(f"\nGlobal Score: {overall.get('global_score', 'N/A')}/100")
        
        if overall.get("top_strengths"):
            print("\nTop Strengths:")
            for strength in overall["top_strengths"]:
                print(f"  ✓ {strength}")
        
        if overall.get("top_problems"):
            print("\nTop Problems:")
            for problem in overall["top_problems"]:
                print(f"  ✗ {problem}")
        
        # Pillar scores
        print("\n" + "=" * 80)
        print("PILLAR SCORES")
        print("=" * 80)
        
        analysis = result.analysis
        pillar_names = {
            "cognitive_friction": "1. Cognitive Friction",
            "emotional_resonance": "2. Emotional Resonance",
            "trust_clarity": "3. Trust & Clarity",
            "decision_simplicity": "4. Decision Simplicity",
            "motivation_profile": "5. Motivation Profile",
            "behavioral_biases": "6. Behavioral Biases",
            "personality_fit": "7. Personality Fit",
            "value_perception": "8. Value Perception",
            "attention_architecture": "9. Attention Architecture",
            "narrative_clarity": "10. Narrative Clarity",
            "emotional_safety": "11. Emotional Safety",
            "actionability": "12. Actionability",
            "identity_alignment": "13. Identity Alignment"
        }
        
        for pillar_key, pillar_name in pillar_names.items():
            pillar_data = analysis.get(pillar_key, {})
            score = pillar_data.get("score", "N/A")
            print(f"{pillar_name}: {score}/100")
        
        # Show human-readable report
        print("\n" + "=" * 80)
        print("HUMAN-READABLE REPORT")
        print("=" * 80)
        print(result.human_readable_report)
        
        # Save full JSON to file
        output_data = {
            "analysis": result.analysis,
            "overall": result.overall
        }
        
        with open("test_psychology_result.json", "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print("\n" + "=" * 80)
        print("✅ Analysis complete!")
        print("Full JSON saved to: test_psychology_result.json")
        print("=" * 80)
        
        return result
        
    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    test_psychology_analysis()

