# Evidence Overlay Implementation Guide

## Backend ✅ Complete

The backend now returns `evidence` field in `/api/analyze/url-human` response:

```json
{
  "evidence": {
    "viewport": "desktop" | "mobile",
    "image_size": [width, height],
    "detected_elements": [
      {
        "id": "cta_1",
        "type": "cta" | "headline" | "pricing" | "testimonial" | "badge" | "logo" | "nav" | "form" | "input",
        "text": "string | null",
        "bbox": [x, y, width, height],
        "confidence": 0.0
      }
    ]
  }
}
```

## Frontend Implementation

### Step 1: Add Types

Create or update `types/evidence.ts`:

```typescript
export type DetectedElementType = 
  | "cta" 
  | "headline" 
  | "pricing" 
  | "testimonial" 
  | "badge" 
  | "logo" 
  | "nav" 
  | "form" 
  | "input";

export interface DetectedElement {
  id: string;
  type: DetectedElementType;
  text?: string | null;
  bbox: [number, number, number, number]; // [x, y, width, height]
  confidence: number;
}

export interface EvidencePayload {
  viewport: "desktop" | "mobile";
  image_size: [number, number]; // [width, height]
  detected_elements: DetectedElement[];
}
```

### Step 2: Update ScreenshotPreviewSection Component

Update `components/ScreenshotPreviewSection.tsx` (or wherever your screenshot component is):

```typescript
import { EvidencePayload, DetectedElementType } from "@/types/evidence";

interface ScreenshotPreviewSectionProps {
  desktopSrc?: string;
  mobileSrc?: string;
  evidence?: EvidencePayload;
  activeTypes?: DetectedElementType[];
  // ... other props
}

export function ScreenshotPreviewSection({
  desktopSrc,
  mobileSrc,
  evidence,
  activeTypes = [],
  ...props
}: ScreenshotPreviewSectionProps) {
  // Determine which screenshot to show based on evidence viewport
  const screenshotSrc = evidence?.viewport === "mobile" ? mobileSrc : desktopSrc;
  const imageSize = evidence?.image_size || [1365, 768];
  
  return (
    <div className="relative">
      {/* Screenshot Image */}
      {screenshotSrc && (
        <img 
          src={screenshotSrc} 
          alt="Screenshot"
          className="w-full h-auto"
        />
      )}
      
      {/* Overlay Elements */}
      {evidence && evidence.detected_elements.length > 0 && (
        <div className="absolute inset-0 pointer-events-none">
          {evidence.detected_elements.map((element) => {
            const [imgW, imgH] = imageSize;
            const [x, y, w, h] = element.bbox;
            
            // Convert pixel coordinates to percentages
            const leftPct = (x / imgW) * 100;
            const topPct = (y / imgH) * 100;
            const wPct = (w / imgW) * 100;
            const hPct = (h / imgH) * 100;
            
            // Check if this element type is active
            const isActive = activeTypes.includes(element.type);
            
            // Color mapping for different element types
            const colorMap: Record<DetectedElementType, string> = {
              cta: "border-blue-400 bg-blue-400/10",
              headline: "border-purple-400 bg-purple-400/10",
              pricing: "border-green-400 bg-green-400/10",
              testimonial: "border-yellow-400 bg-yellow-400/10",
              badge: "border-orange-400 bg-orange-400/10",
              logo: "border-pink-400 bg-pink-400/10",
              nav: "border-gray-400 bg-gray-400/10",
              form: "border-cyan-400 bg-cyan-400/10",
              input: "border-indigo-400 bg-indigo-400/10",
            };
            
            const borderColor = colorMap[element.type] || "border-white/20";
            const activeBorder = isActive ? "border-2 shadow-lg" : "border";
            
            return (
              <div
                key={element.id}
                className={`absolute ${borderColor} ${activeBorder} rounded-md transition-all`}
                style={{
                  left: `${leftPct}%`,
                  top: `${topPct}%`,
                  width: `${wPct}%`,
                  height: `${hPct}%`,
                }}
                title={`${element.type}: ${element.text || element.id}`}
              >
                {/* Optional: Show label */}
                {isActive && element.text && (
                  <div className="absolute -top-6 left-0 bg-black/80 text-white text-xs px-2 py-1 rounded whitespace-nowrap">
                    {element.text.substring(0, 30)}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
```

### Step 3: Update Page Component

Update `app/ai-marketing/decision-brain/page.tsx`:

```typescript
import { EvidencePayload, DetectedElementType } from "@/types/evidence";

// In your component:
const [activeTypes, setActiveTypes] = useState<DetectedElementType[]>([]);
const [evidence, setEvidence] = useState<EvidencePayload | undefined>();

// In handleSubmit, after getting response:
const response = await fetch("/api/analyze/url-human", { ... });
const data = await response.json();

// Extract evidence
if (data.evidence) {
  setEvidence(data.evidence);
}

// Function to map report keywords to element types
function getActiveTypesFromReport(report: string): DetectedElementType[] {
  const types: DetectedElementType[] = [];
  const lowerReport = report.toLowerCase();
  
  if (lowerReport.includes("cta") || lowerReport.includes("call to action")) {
    types.push("cta");
  }
  if (lowerReport.includes("headline") || lowerReport.includes("h1")) {
    types.push("headline");
  }
  if (lowerReport.includes("pricing") || lowerReport.includes("price")) {
    types.push("pricing");
  }
  if (lowerReport.includes("testimonial") || lowerReport.includes("social proof")) {
    types.push("testimonial", "badge", "logo");
  }
  if (lowerReport.includes("form")) {
    types.push("form", "input");
  }
  
  return types;
}

// When report is displayed or clicked:
useEffect(() => {
  if (data?.report) {
    const types = getActiveTypesFromReport(data.report);
    setActiveTypes(types);
  }
}, [data?.report]);

// Render:
<ScreenshotPreviewSection
  desktopSrc={desktopSrc}
  mobileSrc={mobileSrc}
  evidence={evidence}
  activeTypes={activeTypes}
/>
```

### Step 4: Optional - Click to Highlight

Add click handlers to highlight elements:

```typescript
// In ScreenshotPreviewSection:
const [clickedElementId, setClickedElementId] = useState<string | null>(null);

// Add onClick to overlay divs:
<div
  key={element.id}
  onClick={() => setClickedElementId(element.id === clickedElementId ? null : element.id)}
  className={`... ${element.id === clickedElementId ? "ring-2 ring-yellow-400" : ""}`}
  // ... rest of props
/>
```

## Testing

1. Test with a URL that has clear CTAs and headlines
2. Verify bbox coordinates match screenshot positions
3. Test with both desktop and mobile screenshots
4. Verify activeTypes highlighting works when report mentions keywords

## Notes

- bbox coordinates are in screenshot pixel coordinates
- Convert to percentages based on `evidence.image_size`
- If `evidence` is missing, overlays won't render (graceful degradation)
- Element detection may take a few seconds (async Vision API call)


