"""
Client-Ready Decision Report Formatter v1.0

Transforms raw decision analysis into a clear, structured, client-ready decision report
that communicates insight, confidence, and action — without overwhelming or sounding generic.

Core Principle: Insight must come before recommendation. Diagnosis must come before action.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ClientReportFormatter:
    """
    Formats decision engine output into client-ready reports.
    
    The report structure follows a fixed 7-section format:
    1. Executive Decision Summary
    2. Context Snapshot
    3. Decision Failure Breakdown
    4. What To Fix First
    5. Actionable Recommendations
    6. What This Will Improve
    7. Next Diagnostic Step
    """
    
    # Blocker category mapping for confidence assessment
    BLOCKER_CATEGORIES = {
        "Outcome Unclear": "cognitive",
        "Trust Gap": "trust",
        "Risk Not Addressed": "risk",
        "Effort Too High": "cognitive",
        "Commitment Anxiety": "identity"
    }
    
    # Confidence levels based on blocker type and context
    CONFIDENCE_MAPPING = {
        "Outcome Unclear": 0.75,
        "Trust Gap": 0.80,
        "Risk Not Addressed": 0.85,
        "Effort Too High": 0.70,
        "Commitment Anxiety": 0.75
    }
    
    def __init__(self):
        """Initialize the formatter."""
        pass
    
    def format_report(
        self,
        decision_output: Dict[str, Any],
        context_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Format decision engine output into client-ready report.
        
        Args:
            decision_output: DecisionEngineOutput dict with keys:
                - decision_blocker
                - why
                - where
                - what_to_change_first
                - expected_decision_lift
                - memory (optional)
                - chronic_patterns (optional)
            context_data: Optional context data with:
                - business_type (optional)
                - price_level (optional)
                - decision_depth (optional)
                - user_intent_stage (optional)
                - url (optional)
                - platform (optional)
        
        Returns:
            Formatted markdown report string
        """
        blocker = decision_output.get("decision_blocker", "")
        why = decision_output.get("why", "")
        where = decision_output.get("where", "")
        what_to_change = decision_output.get("what_to_change_first", "")
        expected_lift = decision_output.get("expected_decision_lift", "")
        memory = decision_output.get("memory")
        chronic_patterns = decision_output.get("chronic_patterns")
        
        # Extract context
        business_type = context_data.get("business_type") if context_data else None
        price_level = context_data.get("price_level") if context_data else None
        decision_depth = context_data.get("decision_depth") if context_data else None
        user_intent_stage = context_data.get("user_intent_stage") if context_data else None
        url = context_data.get("url") if context_data else None
        platform = context_data.get("platform") if context_data else None
        
        # Calculate confidence
        base_confidence = self.CONFIDENCE_MAPPING.get(blocker, 0.75)
        confidence_pct = int(base_confidence * 100)
        
        # Determine category
        category = self.BLOCKER_CATEGORIES.get(blocker, "cognitive")
        
        # Parse why into sentences (should be exactly 2 per decision engine output)
        why_sentences = [s.strip() for s in why.replace('!', '.').replace('?', '.').split('.') if s.strip()]
        primary_reason = why_sentences[0] if why_sentences else f"Users hesitate due to {blocker}."
        secondary_reason = why_sentences[1] if len(why_sentences) > 1 else None
        
        # Build report sections
        sections = []
        
        # 1. Executive Decision Summary
        sections.append(self._format_executive_summary(
            blocker, confidence_pct, category, primary_reason
        ))
        
        # 2. Context Snapshot
        sections.append(self._format_context_snapshot(
            business_type, price_level, decision_depth, user_intent_stage,
            url, platform, context_data
        ))
        
        # 3. Decision Failure Breakdown
        sections.append(self._format_decision_failure_breakdown(
            blocker, primary_reason, secondary_reason, where, category
        ))
        
        # 4. What To Fix First
        sections.append(self._format_what_to_fix_first(
            blocker, what_to_change, where, category
        ))
        
        # 5. Actionable Recommendations
        sections.append(self._format_actionable_recommendations(
            blocker, what_to_change, where, category
        ))
        
        # 6. What This Will Improve
        sections.append(self._format_outcome_projection(
            blocker, expected_lift, category
        ))
        
        # 7. Decision Stage Assessment (if stage inference available)
        decision_stage_assessment = decision_output.get("decision_stage_assessment")
        if decision_stage_assessment:
            sections.append(self._format_decision_stage_assessment(
                decision_stage_assessment, blocker
            ))
        
        # 8. Decision History Insight (if memory exists)
        decision_history_insight = decision_output.get("decision_history_insight")
        if decision_history_insight:
            sections.append(self._format_decision_history_insight(
                decision_history_insight
            ))
        
        # 8b. Decision Journey Insight (Journey × Memory integration)
        if decision_history_insight and decision_history_insight.get("journey_insight"):
            sections.append(self._format_decision_journey_insight(
                decision_history_insight.get("journey_insight")
            ))
        
        # 9. Next Diagnostic Step
        sections.append(self._format_next_diagnostic_step(
            blocker, memory, chronic_patterns, decision_history_insight
        ))
        
        # Combine all sections
        report = "\n\n".join(sections)
        
        # Add header
        header = f"# Decision Analysis Report\n\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n"
        if url:
            header += f"*URL: {url}*\n"
        
        return header + "\n\n" + report
    
    def _format_executive_summary(
        self,
        blocker: str,
        confidence_pct: int,
        category: str,
        primary_reason: str
    ) -> str:
        """Format Executive Decision Summary section."""
        category_label = {
            "risk": "risk",
            "trust": "trust",
            "identity": "identity",
            "cognitive": "cognitive"
        }.get(category, "cognitive")
        
        # Extract the core issue from primary_reason
        # This is a simplified extraction - in production, you might use NLP
        issue_summary = primary_reason
        
        return f"""## 1️⃣ Executive Decision Summary

The primary reason users hesitate is **{blocker}**, with an estimated confidence of **{confidence_pct}%**.

This indicates a **{category_label}** failure rather than a surface-level CTA issue.

{primary_reason}"""
    
    def _format_context_snapshot(
        self,
        business_type: Optional[str],
        price_level: Optional[str],
        decision_depth: Optional[str],
        user_intent_stage: Optional[str],
        url: Optional[str],
        platform: Optional[str],
        context_data: Optional[Dict[str, Any]]
    ) -> str:
        """Format Context Snapshot section."""
        lines = ["## 2️⃣ Context Snapshot"]
        
        # Build context from available data
        context_items = []
        
        if business_type:
            context_items.append(f"**Business type:** {business_type}")
        elif platform:
            context_items.append(f"**Platform:** {platform}")
        
        if price_level:
            context_items.append(f"**Price level:** {price_level}")
        
        if decision_depth:
            context_items.append(f"**Decision depth:** {decision_depth}")
        
        if user_intent_stage:
            context_items.append(f"**User intent stage:** {user_intent_stage}")
        
        # Determine context confidence
        if context_data and any([business_type, price_level, decision_depth, user_intent_stage]):
            context_confidence = "explicit"
        else:
            context_confidence = "inferred"
        
        context_items.append(f"**Context confidence:** {context_confidence}")
        
        if context_items:
            lines.append("\n".join(context_items))
        else:
            lines.append("Context inferred from page structure and decision elements.")
            lines.append("")
            lines.append("**Note:** Limited context data available. Analysis based on visible decision elements.")
        
        return "\n".join(lines)
    
    def _format_decision_failure_breakdown(
        self,
        blocker: str,
        primary_reason: str,
        secondary_reason: Optional[str],
        where: str,
        category: str
    ) -> str:
        """Format Decision Failure Breakdown section."""
        lines = ["## 3️⃣ Decision Failure Breakdown"]
        
        # Primary outcome
        lines.append(f"### Primary Outcome: {blocker}")
        lines.append("")
        lines.append(f"**What breaks psychologically:**")
        lines.append(f"{primary_reason}")
        lines.append("")
        lines.append(f"**How it shows up:**")
        lines.append(f"This manifests at the **{where}** section, where users encounter the decision point but lack the necessary clarity or confidence to proceed.")
        lines.append("")
        lines.append(f"**Context interaction:**")
        
        # Context-specific explanation based on category
        category_explanations = {
            "cognitive": "The cognitive load at this decision point exceeds what users can process comfortably, creating hesitation.",
            "trust": "Trust signals are insufficient or misaligned with the decision stakes, causing users to question credibility.",
            "risk": "Risk mitigation information is absent or unclear, leaving users uncertain about potential negative outcomes.",
            "identity": "The commitment required feels misaligned with the user's self-perception or current situation."
        }
        lines.append(category_explanations.get(category, "The decision point creates psychological friction that prevents forward movement."))
        
        # Secondary outcome (if exists)
        if secondary_reason:
            lines.append("")
            lines.append(f"### Secondary Consideration")
            lines.append("")
            lines.append(f"{secondary_reason}")
            lines.append("")
            lines.append("This secondary factor amplifies the primary blocker, creating a compound hesitation effect.")
        
        return "\n".join(lines)
    
    def _format_what_to_fix_first(
        self,
        blocker: str,
        what_to_change: str,
        where: str,
        category: str
    ) -> str:
        """Format What To Fix First section."""
        lines = ["## 4️⃣ What To Fix First"]
        
        # Priority logic based on category
        priority_explanations = {
            "cognitive": "Addressing cognitive clarity must come first because users cannot make decisions when they don't understand what they're deciding.",
            "trust": "Trust must be established before any other intervention can be effective, as users won't engage with untrusted offers.",
            "risk": "Risk mitigation must be addressed immediately, as unresolved risk concerns will override all other messaging.",
            "identity": "Commitment alignment must be fixed first, as users won't proceed if the decision feels misaligned with their identity or situation."
        }
        
        priority_explanation = priority_explanations.get(category, "This intervention addresses the core psychological barrier preventing decision.")
        
        lines.append(f"**First intervention priority:** {what_to_change}")
        lines.append("")
        lines.append(f"**Why this comes first:**")
        lines.append(priority_explanation)
        lines.append("")
        lines.append("**What happens if ignored:**")
        
        ignore_consequences = {
            "cognitive": "Users will continue to hesitate due to unclear outcomes, regardless of how compelling other elements are.",
            "trust": "No amount of optimization elsewhere will overcome trust deficits at the decision point.",
            "risk": "Risk concerns will persist and likely cause abandonment, even if other improvements are made.",
            "identity": "Users will feel the commitment is wrong for them, leading to hesitation or abandonment."
        }
        lines.append(ignore_consequences.get(category, "The core hesitation will persist, limiting the effectiveness of other changes."))
        
        return "\n".join(lines)
    
    def _format_actionable_recommendations(
        self,
        blocker: str,
        what_to_change: str,
        where: str,
        category: str
    ) -> str:
        """Format Actionable Recommendations section."""
        lines = ["## 5️⃣ Actionable Recommendations"]
        
        # Group recommendations by type
        lines.append("### Message-Level Changes")
        lines.append("")
        lines.append(f"**Addressing {blocker}:**")
        lines.append(f"- {what_to_change}")
        lines.append("")
        
        # Structure-level changes (generic guidance)
        lines.append("### Structure-Level Changes")
        lines.append("")
        structure_guidance = {
            "cognitive": f"Ensure the **{where}** section presents information in a clear hierarchy, with the most critical decision information first.",
            "trust": f"Position trust signals prominently in the **{where}** section, making them visible before the decision point.",
            "risk": f"Include risk mitigation information in the **{where}** section, making policies clear and accessible.",
            "identity": f"Adjust the commitment framing in the **{where}** section to align with user expectations and reduce perceived commitment burden."
        }
        lines.append(structure_guidance.get(category, f"Review the information architecture of the **{where}** section to reduce friction."))
        
        # Timing/flow changes (if relevant)
        if category in ["cognitive", "identity"]:
            lines.append("")
            lines.append("### Timing / Flow Changes")
            lines.append("")
            if category == "cognitive":
                lines.append("Consider progressive disclosure: reveal information in stages rather than all at once, allowing users to process each element before moving forward.")
            elif category == "identity":
                lines.append("Allow users to adjust commitment level or see what happens after the decision before requiring full commitment.")
        
        return "\n".join(lines)
    
    def _format_outcome_projection(
        self,
        blocker: str,
        expected_lift: str,
        category: str
    ) -> str:
        """Format What This Will Improve section."""
        lines = ["## 6️⃣ What This Will Improve"]
        
        # Behavioral improvement description
        improvement_descriptions = {
            "cognitive": "These changes are expected to reduce hesitation caused by unclear outcomes and make the decision feel clearer and more manageable.",
            "trust": "These changes are expected to reduce hesitation caused by trust gaps and make the decision feel safer and more credible.",
            "risk": "These changes are expected to reduce hesitation caused by unaddressed risk concerns and make the decision feel safer and more reversible.",
            "identity": "These changes are expected to reduce hesitation caused by commitment anxiety and make the decision feel lighter and more aligned with user needs."
        }
        
        lines.append(improvement_descriptions.get(category, "These changes are expected to reduce hesitation and make the decision feel more accessible."))
        lines.append("")
        lines.append(f"**Expected conversion lift:** {expected_lift}")
        lines.append("")
        lines.append("**Directional expectations:**")
        lines.append("- Reduced hesitation at the decision point")
        lines.append("- Increased clarity about what happens after deciding")
        lines.append("- Improved alignment between user expectations and decision requirements")
        lines.append("")
        lines.append("*Note: Actual results will depend on implementation quality, market conditions, and user segment characteristics.*")
        
        return "\n".join(lines)
    
    def _format_decision_stage_assessment(
        self,
        stage_assessment: Dict[str, Any],
        blocker: str
    ) -> str:
        """Format Decision Stage Assessment section."""
        lines = ["## 7️⃣ Decision Stage Assessment"]
        lines.append("")
        
        stage = stage_assessment.get("stage", "unknown")
        confidence = stage_assessment.get("confidence", 0)
        explanation = stage_assessment.get("explanation", "")
        friction_severity = stage_assessment.get("friction_severity", "unknown")
        friction_reasoning = stage_assessment.get("friction_reasoning", "")
        friction_recommendation = stage_assessment.get("friction_recommendation", "")
        
        # Stage name formatting
        stage_names = {
            "orientation": "Orientation",
            "sense_making": "Sense-Making",
            "evaluation": "Evaluation",
            "commitment": "Commitment",
            "post_decision_validation": "Post-Decision Validation"
        }
        stage_display = stage_names.get(stage, stage.title())
        
        lines.append(f"**Identified Decision Stage:** {stage_display}")
        lines.append(f"**Confidence:** {confidence:.0f}%")
        lines.append("")
        lines.append(f"**Why this stage:** {explanation}")
        lines.append("")
        
        # Friction severity
        lines.append("### Friction Severity at This Stage")
        lines.append("")
        
        severity_labels = {
            "natural": "✅ Natural",
            "acceptable": "✅ Acceptable",
            "warning": "⚠️ Warning",
            "critical": "🚨 Critical",
            "high_risk": "🚨 High Risk"
        }
        severity_display = severity_labels.get(friction_severity, friction_severity.title())
        
        lines.append(f"**{blocker} at {stage_display} stage:** {severity_display}")
        lines.append("")
        lines.append(f"**Reasoning:** {friction_reasoning}")
        lines.append("")
        lines.append(f"**Recommendation:** {friction_recommendation}")
        lines.append("")
        
        # Stage-specific guidance
        if friction_severity in ["natural", "acceptable"]:
            lines.append("**Important:** This friction is expected or acceptable at this stage. ")
            lines.append("Focus on guidance and education rather than aggressive fixes.")
        elif friction_severity == "warning":
            lines.append("**Note:** This friction should be addressed, but may not require immediate action.")
        else:
            lines.append("**Action Required:** This friction must be addressed to prevent abandonment.")
        
        return "\n".join(lines)
    
    def _format_decision_history_insight(
        self,
        history_insight: Dict[str, Any]
    ) -> str:
        """Format Decision History Insight section."""
        lines = ["## 8️⃣ Decision History Insight"]
        lines.append("")
        lines.append("*This analysis is informed by prior decision history for this context.*")
        lines.append("")
        
        # What has failed
        what_failed = history_insight.get("what_failed", [])
        if what_failed:
            lines.append("### What Has Already Failed")
            lines.append("")
            for item in what_failed:
                lines.append(f"- {item}")
            lines.append("")
        
        # What has improved
        what_improved = history_insight.get("what_improved", [])
        if what_improved:
            lines.append("### What Has Improved")
            lines.append("")
            for item in what_improved:
                lines.append(f"- {item}")
            lines.append("")
        
        # What remains unresolved
        what_unresolved = history_insight.get("what_remains_unresolved", [])
        if what_unresolved:
            lines.append("### What Remains Unresolved")
            lines.append("")
            for item in what_unresolved:
                lines.append(f"- {item}")
            lines.append("")
        
        # Why still hesitating
        why_hesitating = history_insight.get("why_still_hesitating", "")
        if why_hesitating:
            lines.append("### Why Users Are Still Hesitating")
            lines.append("")
            lines.append(why_hesitating)
            lines.append("")
        
        # Trajectory summary
        trajectory = history_insight.get("trajectory_summary", "")
        if trajectory:
            lines.append("### Trajectory Summary")
            lines.append("")
            lines.append(trajectory)
            lines.append("")
        
        # Fatigue analysis
        fatigue = history_insight.get("fatigue")
        if fatigue:
            lines.append("### Decision Fatigue Analysis")
            lines.append("")
            lines.append(f"**Fatigue Level:** {fatigue.get('level', 'unknown').title()}")
            lines.append("")
            indicators = fatigue.get("indicators", [])
            if indicators:
                lines.append("**Indicators:**")
                for indicator in indicators:
                    lines.append(f"- {indicator}")
                lines.append("")
            recommendation = fatigue.get("recommendation", "")
            if recommendation:
                lines.append(f"**Recommendation:** {recommendation}")
                lines.append("")
        
        # Trust dynamics
        trust = history_insight.get("trust_dynamics")
        if trust:
            lines.append("### Trust Dynamics")
            lines.append("")
            trend = trust.get("trend", "unknown")
            consistency = trust.get("consistency", "unknown")
            lines.append(f"**Trust Debt Trend:** {trend.title()}")
            lines.append(f"**Trust Consistency:** {consistency.replace('_', ' ').title()}")
            lines.append("")
            recommendation = trust.get("recommendation", "")
            if recommendation:
                lines.append(f"**Recommendation:** {recommendation}")
                lines.append("")
        
        return "\n".join(lines)
    
    def _format_decision_journey_insight(
        self,
        journey_insight: Dict[str, Any]
    ) -> str:
        """Format Decision Journey Insight section (Journey × Memory integration)."""
        lines = ["## 🔄 Decision Journey Insight"]
        lines.append("")
        lines.append("*This analysis combines inferred decision stages with decision memory to understand movement, stagnation, or regression over time.*")
        lines.append("")
        
        # Observed stage trajectory
        observed_trajectory = journey_insight.get("observed_stage_trajectory", "")
        if observed_trajectory:
            lines.append("### Observed Stage Trajectory")
            lines.append("")
            lines.append(f"**Stage sequence:** {observed_trajectory}")
            lines.append("")
        
        # Interpretation
        interpretation = journey_insight.get("interpretation", "")
        if interpretation:
            interpretation_labels = {
                "progress": "✅ Progress",
                "stuck": "⚠️ Stuck",
                "regression": "🚨 Regression"
            }
            interpretation_display = interpretation_labels.get(interpretation, interpretation.title())
            lines.append("### Interpretation")
            lines.append("")
            lines.append(f"**Status:** {interpretation_display}")
            lines.append("")
        
        # What is preventing advancement
        what_preventing = journey_insight.get("what_is_preventing_advancement", "")
        if what_preventing:
            lines.append("### What Is Preventing Advancement")
            lines.append("")
            lines.append(what_preventing)
            lines.append("")
        
        # Action recommendation
        action_recommendation = journey_insight.get("action_recommendation", "")
        if action_recommendation:
            action_labels = {
                "fix": "🔧 Fix",
                "reframe": "🔄 Reframe",
                "unlock": "🔓 Unlock",
                "wait": "⏳ Wait"
            }
            action_display = action_labels.get(action_recommendation, action_recommendation.title())
            lines.append("### Action Recommendation")
            lines.append("")
            lines.append(f"**Recommended action:** {action_display}")
            lines.append("")
            
            # Action-specific guidance
            if action_recommendation == "fix":
                lines.append("**Guidance:** The regression or critical stagnation requires immediate intervention. Address the identified blocker to prevent further retreat.")
            elif action_recommendation == "unlock":
                lines.append("**Guidance:** Users are stuck at a stage. Focus on unlocking progression by resolving the blocker preventing stage shift. Do not force conversion.")
            elif action_recommendation == "reframe":
                lines.append("**Guidance:** The decision framing may need adjustment. Consider how the offer or messaging aligns with the current decision stage.")
            else:  # wait
                lines.append("**Guidance:** The decision process is progressing normally. Support the journey rather than pushing premature commitment.")
            lines.append("")
        
        # Trajectory analysis details
        trajectory_analysis = journey_insight.get("trajectory_analysis")
        if trajectory_analysis:
            lines.append("### Trajectory Analysis Details")
            lines.append("")
            trajectory_type = trajectory_analysis.get("trajectory_type", "")
            if trajectory_type:
                type_labels = {
                    "forward_progress": "✅ Forward Progress",
                    "stagnation": "⚠️ Stagnation",
                    "regression": "🚨 Regression"
                }
                type_display = type_labels.get(trajectory_type, trajectory_type.title())
                lines.append(f"**Trajectory type:** {type_display}")
                lines.append("")
            
            interpretation_detail = trajectory_analysis.get("interpretation", "")
            if interpretation_detail:
                lines.append(f"**Interpretation:** {interpretation_detail}")
                lines.append("")
            
            blocker_identified = trajectory_analysis.get("blocker_identified")
            if blocker_identified:
                lines.append(f"**Blocker identified:** {blocker_identified}")
                lines.append("")
            
            recommendation = trajectory_analysis.get("recommendation", "")
            if recommendation:
                lines.append(f"**Recommendation:** {recommendation}")
                lines.append("")
        
        return "\n".join(lines)
    
    def _format_next_diagnostic_step(
        self,
        blocker: str,
        memory: Optional[Dict[str, Any]],
        chronic_patterns: Optional[Dict[str, Any]],
        history_insight: Optional[Dict[str, Any]] = None
    ) -> str:
        """Format Next Diagnostic Step section."""
        lines = ["## 9️⃣ Next Diagnostic Step"]
        
        # Check for chronic patterns
        if chronic_patterns:
            lines.append("**Pattern detected:** Recurring decision blockers suggest deeper structural issues.")
            lines.append("")
            lines.append("**Recommended next step:**")
            lines.append("Journey-level decision mapping to identify where hesitation patterns emerge across the user path, not just at this single decision point.")
        elif memory and memory.get("times_seen", 0) > 1:
            lines.append("**Pattern emerging:** This URL has been analyzed multiple times with similar blockers.")
            lines.append("")
            lines.append("**Recommended next step:**")
            lines.append("Cross-page consistency check to ensure decision clarity is maintained across all touchpoints in the user journey.")
        else:
            lines.append("**Strategic follow-up:**")
            lines.append("")
            lines.append("Once this intervention is implemented and measured, consider:")
            lines.append("- Deeper user intent analysis to understand what drives hesitation in your specific audience")
            lines.append("- Journey-level decision mapping to identify other friction points in the conversion path")
            lines.append("- Cross-page consistency check to ensure decision clarity is maintained across touchpoints")
        
        return "\n".join(lines)


def format_decision_report(
    decision_output: Dict[str, Any],
    context_data: Optional[Dict[str, Any]] = None
) -> str:
    """
    Convenience function to format a decision report.
    
    Args:
        decision_output: DecisionEngineOutput dict
        context_data: Optional context data
    
    Returns:
        Formatted markdown report string
    """
    formatter = ClientReportFormatter()
    return formatter.format_report(decision_output, context_data)



