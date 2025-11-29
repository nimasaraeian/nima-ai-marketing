# تست /api/brain Endpoint

## Request

```json
{
  "role": "ai_marketing_strategist",
  "locale": "tr-TR",
  "city": "Istanbul",
  "industry": "restaurant",
  "channel": "Instagram Ads",
  "query": "I own a mid-range restaurant in Kadıköy, Istanbul. Here is my current Instagram ad copy: 'Delicious food, cozy vibes. Visit us tonight!' Our CTR is low and people save the post but don't click. Analyze this ad using behavioral marketing and AI, suggest 3-5 concrete new ad variants, and propose 2 A/B test ideas with clear metrics."
}
```

## Response

**Quality Score:** 5/5

### Quality Checks

- has_examples: True
- has_localization: True
- has_action_plan: True
- has_metrics: True
- has_analysis: True

### Full Response

## Snapshot (Context Summary)

- **Business Type:** Mid-range restaurant in Kadıköy, Istanbul.
- **Main Symptom:** Low CTR on Instagram ads, although users save the post.
- **Channel:** Instagram Ads.

## Root-Cause Analysis (Layered)

### Offer & Message Issues
- The current ad copy lacks specificity about the experience, menu highlights, or unique offerings that differentiate the restaurant.
- It doesn't create a strong call to action or urgency, which is essential for driving clicks.

### Targeting & Audience Mismatch
- The ad may not resonate with the exact audience in Kadıköy, especially considering the competitive landscape of dining options.

### Funnel & Landing Page Issues
- The post may not lead to a compelling landing page that matches the promise of the ad, leading to a disconnect once users click through.

### Channel/Creative Mismatch
- The creative elements (visuals, tone) may not align with the preferences of Instagram users in Istanbul, particularly younger demographics who prefer engaging, visually appealing content.

## 4P Scan (Applied)

### Product
- Emphasize unique dishes, seasonal ingredients, or chef specialties that make the restaurant stand out.

### Price
- Consider including a special offer or promotion to increase perceived value (e.g., "Happy Hour Discounts", "Free Dessert with Main Course").

### Place
- Leverage the vibrant atmosphere of Kadıköy, highlighting its appeal to both locals and tourists.

### Promotion
- The current ad lacks emotional or sensory appeal. Adding elements that evoke taste, experience, or social proof can enhance engagement.

### Concrete Examples

- **Headline Example:** "Experience Istanbul’s Flavor at Our Cozy Kadıköy Hideaway!"
- **Hook Idea:** "Savor the Taste of Our Signature Dish—Book Your Table Now!"
- **Offer Variation:** "Enjoy 20% Off Your First Visit! Limited Time Only!"
- **Retargeting Copy:** "You Saved Us! Come Taste What You’ve Been Missing—Special Discounts Await!"

## Action Plan (0–7 days / 7–30 days)

### Phase 1 (0–7 days) — Quick Diagnosis & A/B Tests

1. **Ad Variants:** Create 3-5 new ad creatives with the following concepts:
   - **Ad Variant 1:** Focus on a signature dish: "Try our famous Kadıköy Kebab—The Taste of Tradition Awaits! 🍽️ Reserve Now!"
   - **Ad Variant 2:** Highlight ambiance: "Join Us for Dinner—Cozy Vibes & Delicious Food in the Heart of Kadıköy! 🌟 Book Your Table Tonight!"
   - **Ad Variant 3:** Promote a special offer: "Limited Time: 20% Off All Main Courses This Week! Click to Claim Your Discount!"
   - **Ad Variant 4:** Use user-generated content: "See Why Locals Love Us! Check Out Our Customers’ Favorite Dishes—Click for More!"
   - **Ad Variant 5:** Time-limited event: "Join Our Wine & Dine Night—Book Your Spot Before It’s Gone!"

2. **Metrics to Observe:** Focus on CTR and engagement metrics (likes, shares, saves).

### Phase 2 (7–30 days) — Scaling & Refinement

1. **A/B Test Ideas:**
   - **Test Idea 1:** Compare ad variants focusing on ambiance vs. specific dishes. Measure CTR and engagement to determine which theme resonates better.
     - **Metrics:** CTR, engagement rate (likes, shares), and conversion rate (bookings).
   - **Test Idea 2:** Test different call-to-action phrases, such as "Reserve Your Table Now!" vs. "Claim Your Discount Today!" 
     - **Metrics:** CTR and conversion rate for reservations.

### Metrics & Targets
- **Target Range for CTR Improvement:** Aim to increase CTR from the current rate (e.g., if it's 0.5%) to at least 1.5–2% within the first month.
- **KPIs to Track Daily vs. Weekly:** Daily tracking of CTR and weekly analysis of bookings generated from the ads.

## Risk & Reality Check
- If the product-market fit is weak (e.g., menu items don’t appeal to the target audience), no amount of advertising will fix it. Ensure the menu aligns with local preferences, and consider soliciting feedback from customers to adjust offerings accordingly.