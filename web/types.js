/**
 * API Types - Shared between Frontend and Backend
 * 
 * این فایل types مشترک بین Frontend و Backend را تعریف می‌کند.
 * برای هماهنگی، هر دو طرف باید از این ساختار استفاده کنند.
 * 
 * Last Updated: Generated from shared/api-types.json
 */

/**
 * @typedef {Object} CognitiveFrictionAnalysis
 * @property {number} score - Score from 0-100
 * @property {string[]} [signals] - Friction signals detected
 * @property {string[]} [hotspots] - Exact friction hotspots
 * @property {string[]} [issues] - Issues list
 * @property {string[]} [reasons] - Explanation of score
 * @property {string} rewrite - Improved low-friction version
 * @property {string[]} [keyDecisionBlockers] - Main blockers
 * @property {string[]} [overload_factors] - Cognitive overload factors
 * @property {string[]} [cognitiveOverloadFactors] - Cognitive overload factors (alternative)
 */

/**
 * @typedef {Object} EmotionalResonanceAnalysis
 * @property {number} score - Score from 0-100
 * @property {string} [emotion_detected] - Primary emotion detected
 * @property {string} [emotion_required] - Emotion that should be triggered
 * @property {string} [mismatch] - Report on emotional mismatch
 * @property {string[]} [resistance_factors] - Emotional resistance factors
 * @property {string[]} [emotionalResistanceFactors] - Emotional resistance factors (alternative)
 * @property {string} rewrite - Improved emotional version
 */

/**
 * @typedef {Object} TrustClarityAnalysis
 * @property {number} score - Score from 0-100
 * @property {number} [trust_score] - Trust score 0-100 (alternative)
 * @property {string[]} [issues] - Issues list
 * @property {string[]} [breakpoints] - Trust breakpoints
 * @property {string[]} [trustBreakpoints] - Trust breakpoints (alternative)
 * @property {string} [rewrite] - Improved trust-building version
 */

/**
 * @typedef {Object} MotivationProfileAnalysis
 * @property {number} score - Score from 0-100
 * @property {string} [dominant] - Dominant SDT motivator
 * @property {string[]} [misalignment_signals] - Misalignment signals
 * @property {string} [rewrite] - SDT-aligned rewrite
 */

/**
 * @typedef {Object} PsychologyAnalysis
 * @property {CognitiveFrictionAnalysis} cognitive_friction
 * @property {EmotionalResonanceAnalysis} emotional_resonance
 * @property {TrustClarityAnalysis} trust_clarity
 * @property {MotivationProfileAnalysis} [motivation_profile]
 */

/**
 * @typedef {Object} OverallSummary
 * @property {number|null} global_score - Global score 0-100
 * @property {string} [interpretation] - Interpretation text
 * @property {number|null} decision_likelihood_percentage - Decision likelihood 0-100
 * @property {number|null} [decision_likelihood] - Decision likelihood (alternative)
 * @property {number|null} [conversion_lift_estimate] - Conversion lift estimate -100 to +100
 * @property {number|null} [conversionLiftEstimate] - Conversion lift estimate (alternative)
 * @property {Array<string|Object>} [priority_fixes] - Priority fixes (can be strings or objects)
 * @property {string[]} [recommendedQuickWins] - Quick wins
 * @property {string[]} [quick_wins] - Quick wins (alternative)
 * @property {string[]} [recommendedDeepChanges] - Deep changes
 * @property {string[]} [final_recommendations] - Final recommendations
 * @property {string[]} [strengths] - Strengths list
 * @property {string} [summary] - Summary text
 * @property {string} [explanationSummary] - Explanation summary
 */

/**
 * @typedef {Object} VisualTrust
 * @property {string} [label] - Trust label (high_trust, medium_trust, low_trust)
 * @property {number|null} [score_numeric] - Numeric trust score
 * @property {Object} [scores] - Per-class probabilities
 * @property {string} [error] - Error message if analysis failed
 * @property {boolean} [model_missing] - Whether model is missing
 */

/**
 * @typedef {Object} VisualLayer
 * @property {string} [visual_trust_label] - Trust label
 * @property {number|null} [visual_trust_score] - Trust score
 * @property {Object} [visual_trust_breakdown] - Score breakdown
 * @property {Object} [visual_trust_scores] - Trust scores
 * @property {string} [visual_comment] - Visual comment
 */

/**
 * @typedef {Object} PsychologyAnalysisResult
 * @property {PsychologyAnalysis} analysis - Analysis results for all pillars
 * @property {OverallSummary} overall - Overall summary and scores
 * @property {string} [human_readable_report] - Human-readable report
 * @property {VisualTrust} [visual_trust] - Visual trust analysis (if image provided)
 * @property {VisualLayer} [visual_layer] - Visual layer data (if image provided)
 */

/**
 * @typedef {Object} CognitiveFrictionResult
 * @property {number} frictionScore - Overall cognitive friction (0-100)
 * @property {number} trustScore - Perceived trust level (0-100)
 * @property {number} emotionalClarityScore - Emotional clarity & resonance (0-100)
 * @property {number} motivationMatchScore - Alignment with user motivation (0-100)
 * @property {number} decisionProbability - Likelihood user will decide/act (0-1)
 * @property {number} conversionLiftEstimate - % improvement if issues fixed (-100 to +100)
 * @property {string[]} keyDecisionBlockers - Main blockers
 * @property {string[]} emotionalResistanceFactors - Emotional resistance factors
 * @property {string[]} cognitiveOverloadFactors - Cognitive overload factors
 * @property {string[]} trustBreakpoints - Trust breakpoints
 * @property {string[]} motivationMisalignments - Motivation misalignments
 * @property {string[]} recommendedQuickWins - Actionable quick fixes
 * @property {string[]} recommendedDeepChanges - Deeper structural changes
 * @property {string} explanationSummary - 3-6 sentences summary
 */

// Export types for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        // Types are defined above using JSDoc
    };
}

