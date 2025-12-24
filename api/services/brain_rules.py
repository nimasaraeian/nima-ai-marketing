"""
Heuristic rules engine for page analysis.
Converts page map into findings (issues, quick wins, suggestions).
Now includes page type awareness to apply only relevant rules,
and uses memory-based weights to calibrate severity over time.
"""
from typing import Dict, Any, List, Optional

from api.services.page_type_detection import (
    detect_page_type,
    get_applicable_rules_for_page_type,
    PageType,
)


def run_heuristics(
    capture: Dict[str, Any],
    page_map: Dict[str, Any],
    goal: str = "other",
    locale: str = "fa",
    url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run heuristics on captured page data with page type awareness.
    
    Args:
        capture: Page capture artifacts
        page_map: Extracted page structure
        goal: Page goal (leads, sales, booking, etc.)
        locale: Language locale (fa, en, tr)
        url: Page URL (optional, for page type detection)
        
    Returns:
        Dictionary with page_context (including page_type), findings, and analysis_scope
    """
    # Ensure inputs are dicts
    if not isinstance(capture, dict):
        capture = {}
    if not isinstance(page_map, dict):
        page_map = {}
    
    # Detect page type BEFORE applying rules
    page_type: PageType = detect_page_type(
        url=url or "",
        page_map=page_map,
        capture=capture
    )
    
    # Get applicable rules for this page type
    applicable_rules = get_applicable_rules_for_page_type(page_type)
    
    headlines = page_map.get("headlines", []) if isinstance(page_map, dict) else []
    ctas = page_map.get("ctas", []) if isinstance(page_map, dict) else []
    trust = page_map.get("trust_signals", []) if isinstance(page_map, dict) else []
    
    # Ensure lists
    if not isinstance(headlines, list):
        headlines = []
    if not isinstance(ctas, list):
        ctas = []
    if not isinstance(trust, list):
        trust = []
    
    issues: List[Dict[str, Any]] = []
    quick: List[Dict[str, Any]] = []
    
    # Heuristic 1: clear value prop (only for applicable page types)
    h1 = None
    if headlines and isinstance(headlines, list):
        h1 = next((h for h in headlines if isinstance(h, dict) and h.get("tag") == "h1"), None)
    
    h1_text = h1.get("text", "") if h1 and isinstance(h1, dict) else ""
    if applicable_rules.get("clarity_weak_h1", True) and (not h1 or len(h1_text) < 12):
        issues.append({
            "id": "clarity_weak_h1",
            "severity": "high",
            "problem": "تیتر اصلی (H1) واضح نمی‌گوید دقیقاً چه چیزی برای چه کسی ارائه می‌شود.",
            "why_it_hurts": "وقتی کاربر در چند ثانیه نفهمد پیشنهاد چیست، تصمیم را عقب می‌اندازد یا خارج می‌شود.",
            "where": {
                "section": "hero",
                "selector": "h1",
                "bbox": [0, 0, 0, 0],
                "screenshot_ref": "above_the_fold"
            },
            "evidence": [{
                "type": "text",
                "value": h1_text if h1_text else "H1 یافت نشد"
            }],
            "fix_steps": [
                "H1 را به فرمت «نتیجه + برای چه کسی + تمایز» بازنویسی کن.",
                "یک زیرتیتر 1 جمله‌ای اضافه کن که خروجی/مزیت را مشخص کند.",
                "یک CTA واحد کنار همین متن بگذار."
            ]
        })
    
    # Heuristic 2: primary CTA exists (only for applicable page types)
    if applicable_rules.get("cta_missing", True) and not ctas:
        issues.append({
            "id": "cta_missing",
            "severity": "high",
            "problem": "CTA واضح در صفحه تشخیص داده نشد (دکمه اقدام اصلی).",
            "why_it_hurts": "کاربر نمی‌فهمد قدم بعدی چیست؛ حتی اگر علاقه‌مند باشد، تبدیل اتفاق نمی‌افتد.",
            "where": {
                "section": "hero",
                "selector": "a,button",
                "bbox": [0, 0, 0, 0],
                "screenshot_ref": "above_the_fold"
            },
            "evidence": [{
                "type": "ui",
                "value": "هیچ CTA کاندید پیدا نشد"
            }],
            "fix_steps": [
                "یک CTA اصلی با متن مشخص اضافه کن (مثلاً «Request a Quote» یا «Book a Call»).",
                "CTA را بالای صفحه (ATF) قرار بده.",
                "CTA ثانویه را فقط یکی نگه دار."
            ]
        })
    
    # Heuristic 3: trust near CTA (only for applicable page types)
    if applicable_rules.get("trust_low", True) and not trust:
        issues.append({
            "id": "trust_low",
            "severity": "medium",
            "problem": "نشانه‌های اعتماد نزدیک پیشنهاد/CTA کم است (نظرات، لوگو مشتریان، تضمین، سیاست‌ها).",
            "why_it_hurts": "بدون اعتماد، کاربر ریسک ادراک‌شده را بالا می‌بیند و تصمیم را عقب می‌اندازد.",
            "where": {
                "section": "hero",
                "selector": "body",
                "bbox": [0, 0, 0, 0],
                "screenshot_ref": "above_the_fold"
            },
            "evidence": [{
                "type": "ui",
                "value": "Trust signal کاندید پیدا نشد"
            }],
            "fix_steps": [
                "۲ تستیمونیال کوتاه یا لوگوی ۵ مشتری نزدیک CTA اضافه کن.",
                "یک جمله ریسک‌زدایی اضافه کن (گارانتی/شفافیت روند/زمان تحویل).",
                "لینک Privacy/Terms را در فوتر واضح کن."
            ]
        })
    
    # Quick wins (simple)
    quick.extend([
        {
            "action": "CTA اصلی را یک عدد و پررنگ کن (CTAهای اضافی را کم کن).",
            "where": {"section": "hero", "selector": "a,button"},
            "reason": "کاهش سردرگمی تصمیم"
        },
        {
            "action": "زیر H1 یک جمله توضیح نتیجه/خروجی اضافه کن.",
            "where": {"section": "hero", "selector": "h1"},
            "reason": "افزایش وضوح پیشنهاد"
        },
        {
            "action": "۲ نمونه کار/تستیمونیال نزدیک CTA بگذار.",
            "where": {"section": "hero", "selector": "body"},
            "reason": "کاهش ریسک ادراک‌شده"
        },
        {
            "action": "اگر فرم داری، فیلدهای غیرضروری را حذف کن.",
            "where": {"section": "form", "selector": "form"},
            "reason": "کاهش اصطکاک"
        },
        {
            "action": "تیتر CTA را از مبهم به اقدام‌محور تغییر بده.",
            "where": {"section": "hero", "selector": "a,button"},
            "reason": "افزایش نرخ کلیک"
        }
    ])
    
    # Apply memory-based weights to issues (Decision Brain memory)
    try:
        from api.memory.brain_memory import get_issue_weights_for_page_type

        weights = get_issue_weights_for_page_type(page_type)
    except Exception:
        weights = {}

    severity_map = {
        "low": 1.0,
        "medium": 2.0,
        "high": 3.0,
    }

    for issue in issues:
        if not isinstance(issue, dict):
            continue
        issue_id = str(issue.get("id", ""))
        sev_label = str(issue.get("severity", "medium")).lower()
        base_sev = severity_map.get(sev_label, 2.0)
        weight = float(weights.get(issue_id, 1.0)) if issue_id else 1.0
        final_sev = base_sev * weight

        issue["base_severity_score"] = base_sev
        issue["weight"] = weight
        issue["final_severity_score"] = final_sev

    # Sort issues by calibrated severity (descending)
    issues.sort(key=lambda i: i.get("final_severity_score", 0.0), reverse=True)

    # Filter quick wins based on page type
    # For marketplaces, remove consultation-style quick wins
    if page_type == "ecommerce_marketplace":
        quick = [q for q in quick if "consultation" not in q.get("action", "").lower() and "quote" not in q.get("action", "").lower()]
    
    # Generate page type-specific copy suggestions
    copy_suggestions = {
        "headlines": [],
        "cta_labels": []
    }
    
    if page_type in ["service_landing", "saas_landing"]:
        copy_suggestions["headlines"] = [
            {
                "variant": "A",
                "text": "نتیجه اصلی را در یک جمله واضح بگو (برای مخاطب مشخص).",
                "why": "وضوح پیشنهاد"
            },
            {
                "variant": "B",
                "text": "پیشنهاد + تمایز + زمان/نتیجه را کوتاه کن.",
                "why": "کاهش ابهام"
            },
            {
                "variant": "C",
                "text": "چرا شما؟ یک دلیل قابل باور در تیتر.",
                "why": "افزایش اعتماد"
            }
        ]
        copy_suggestions["cta_labels"] = [
            {
                "variant": "A",
                "text": "Get a Free Consultation",
                "why": "اقدام مشخص"
            },
            {
                "variant": "B",
                "text": "Request a Quote",
                "why": "هم‌راستا با لید"
            }
        ]
    elif page_type == "ecommerce_marketplace":
        # Marketplace-specific suggestions (no consultation CTAs)
        copy_suggestions["headlines"] = [
            {
                "variant": "A",
                "text": "محصول را با مزایای اصلی و مشخصات کلیدی معرفی کن.",
                "why": "وضوح محصول"
            }
        ]
        copy_suggestions["cta_labels"] = [
            {
                "variant": "A",
                "text": "Add to Cart",
                "why": "اقدام خرید"
            }
        ]
    else:
        # Default suggestions for other page types
        copy_suggestions["headlines"] = [
            {
                "variant": "A",
                "text": "نتیجه اصلی را در یک جمله واضح بگو.",
                "why": "وضوح پیشنهاد"
            }
        ]
    
    return {
        "page_context": {
            "page_type": page_type,  # Use detected page type
            "page_type_guess": page_type,  # Keep for backward compatibility
            "industry_guess": "unknown",
            "primary_offer_guess": "",
            "primary_audience_guess": "",
            "intent_guess": "evaluate"
        },
        "findings": {
            "top_issues": issues[:3],
            "quick_wins": quick[:5],
            "copy_suggestions": copy_suggestions,
            "layout_suggestions": []
        },
        "analysis_scope": f"ruleset:{page_type}"  # Indicate which ruleset was used
    }

