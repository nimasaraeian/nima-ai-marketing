"""
Heuristic rules engine for page analysis.
Converts page map into findings (issues, quick wins, suggestions).
"""
from typing import Dict, Any, List


def run_heuristics(
    capture: Dict[str, Any],
    page_map: Dict[str, Any],
    goal: str = "other",
    locale: str = "fa"
) -> Dict[str, Any]:
    """
    Run heuristics on captured page data.
    
    Args:
        capture: Page capture artifacts
        page_map: Extracted page structure
        goal: Page goal (leads, sales, booking, etc.)
        locale: Language locale (fa, en, tr)
        
    Returns:
        Dictionary with page_context and findings
    """
    # Ensure inputs are dicts
    if not isinstance(capture, dict):
        capture = {}
    if not isinstance(page_map, dict):
        page_map = {}
    
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
    
    # Heuristic 1: clear value prop
    h1 = None
    if headlines and isinstance(headlines, list):
        h1 = next((h for h in headlines if isinstance(h, dict) and h.get("tag") == "h1"), None)
    
    h1_text = h1.get("text", "") if h1 and isinstance(h1, dict) else ""
    if not h1 or len(h1_text) < 12:
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
    
    # Heuristic 2: primary CTA exists
    if not ctas:
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
    
    # Heuristic 3: trust near CTA
    if not trust:
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
    
    return {
        "page_context": {
            "page_type_guess": "unknown",
            "industry_guess": "unknown",
            "primary_offer_guess": "",
            "primary_audience_guess": "",
            "intent_guess": "evaluate"
        },
        "findings": {
            "top_issues": issues[:3],
            "quick_wins": quick[:5],
            "copy_suggestions": {
                "headlines": [
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
                ],
                "cta_labels": [
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
            },
            "layout_suggestions": []
        }
    }

