"""
Example: Client-Ready Decision Report

This script demonstrates how to use the client-ready report formatter
to generate professional decision analysis reports.
"""

import json
from decision_engine import DecisionEngineInput, analyze_decision_failure
from api.utils.client_report_formatter import format_decision_report


def example_basic_usage():
    """Example: Basic usage with minimal context"""
    print("=" * 60)
    print("Example 1: Basic Usage")
    print("=" * 60)
    
    # Create input
    input_data = DecisionEngineInput(
        content="""
        Hero: Transform Your Business with AI
        CTA: Get Started Free
        Price: $99/month
        Guarantee: 30-day money-back guarantee
        """
    )
    
    # Get decision analysis
    result = analyze_decision_failure(input_data)
    
    # Format as client-ready report
    report = format_decision_report(
        result.dict(),
        context_data={
            "business_type": "saas",
            "price_level": "visible",
            "decision_depth": "high_stakes"
        }
    )
    
    print(report)
    print("\n")


def example_with_url():
    """Example: Using URL with automatic context extraction"""
    print("=" * 60)
    print("Example 2: With URL (automatic context extraction)")
    print("=" * 60)
    
    # Create input with URL
    input_data = DecisionEngineInput(
        content="https://example.com/pricing",
        url="https://example.com/pricing"
    )
    
    try:
        # Get decision analysis (this will extract snapshot from URL)
        result = analyze_decision_failure(input_data)
        
        # Format as client-ready report
        # Context will be extracted automatically in the endpoint
        report = format_decision_report(
            result.dict(),
            context_data={
                "url": "https://example.com/pricing",
                "platform": "generic"
            }
        )
        
        print(report)
    except Exception as e:
        print(f"Error: {e}")
        print("(This is expected if the URL is not accessible)")
    
    print("\n")


def example_json_output():
    """Example: Getting structured JSON output"""
    print("=" * 60)
    print("Example 3: JSON Output Format")
    print("=" * 60)
    
    input_data = DecisionEngineInput(
        content="""
        Hero: Premium Product
        CTA: Buy Now
        Price: $299
        """
    )
    
    result = analyze_decision_failure(input_data)
    
    # Get both raw analysis and formatted report
    decision_output = result.dict()
    report_text = format_decision_report(
        decision_output,
        context_data={
            "business_type": "ecommerce",
            "price_level": "visible"
        }
    )
    
    # Create structured JSON response
    json_response = {
        "report": report_text,
        "raw_analysis": decision_output,
        "context": {
            "business_type": "ecommerce",
            "price_level": "visible"
        }
    }
    
    print(json.dumps(json_response, indent=2))
    print("\n")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Client-Ready Decision Report Examples")
    print("=" * 60 + "\n")
    
    # Run examples
    example_basic_usage()
    # example_with_url()  # Uncomment if you have a test URL
    example_json_output()
    
    print("\n" + "=" * 60)
    print("To use via API endpoint:")
    print("POST /api/brain/decision-engine/report")
    print("=" * 60)




















