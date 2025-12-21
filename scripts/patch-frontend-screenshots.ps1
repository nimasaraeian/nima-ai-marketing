# PowerShell script to patch frontend screenshot extraction
# This script fixes the TypeError: desktopSrc.substring is not a function

$ErrorActionPreference = "Stop"

Write-Host "🔧 Patching frontend screenshot extraction..." -ForegroundColor Cyan

# Try to find the file in common locations
$possiblePaths = @(
    "..\www.nimasaraeian.com\app\ai-marketing\decision-brain\page.tsx",
    "..\..\www.nimasaraeian.com\app\ai-marketing\decision-brain\page.tsx",
    "C:\Users\$env:USERNAME\Documents\GitHub\www.nimasaraeian.com\app\ai-marketing\decision-brain\page.tsx",
    "app\ai-marketing\decision-brain\page.tsx"
)

$filePath = $null
foreach ($path in $possiblePaths) {
    $fullPath = Resolve-Path $path -ErrorAction SilentlyContinue
    if ($fullPath -and (Test-Path $fullPath)) {
        $filePath = $fullPath.Path
        Write-Host "✅ Found file at: $filePath" -ForegroundColor Green
        break
    }
}

if (-not $filePath) {
    Write-Host "❌ Could not find page.tsx file automatically." -ForegroundColor Red
    Write-Host "Please provide the full path to the file:" -ForegroundColor Yellow
    $filePath = Read-Host "Enter path to app/ai-marketing/decision-brain/page.tsx"
    
    if (-not (Test-Path $filePath)) {
        Write-Host "❌ File not found: $filePath" -ForegroundColor Red
        exit 1
    }
}

Write-Host "📝 Reading file..." -ForegroundColor Cyan
$content = Get-Content $filePath -Raw

# Check if already patched
if ($content -match "data\?\.screenshots\?\.desktop\?\.url") {
    Write-Host "✅ File already patched!" -ForegroundColor Green
    exit 0
}

# Find the problematic lines
$oldPattern = '(?s)(const\s+desktopSrc\s*=.*?)(const\s+mobileSrc\s*=.*?)(console\.log\("📥 Desktop source:".*?desktopSrc\.substring)'

if ($content -match $oldPattern) {
    Write-Host "🔍 Found code to patch..." -ForegroundColor Cyan
    
    # Create replacement
    $replacement = @"
// Extract screenshot URLs (supports new schema: object with .url property)
const getScreenshotUrl = (screenshot: any): string => {
  if (!screenshot) return "";
  if (typeof screenshot === "object" && screenshot?.url) {
    return screenshot.url;
  }
  if (typeof screenshot === "string") {
    return screenshot;
  }
  return "";
};

const desktopSrc = getScreenshotUrl(data?.screenshots?.desktop);
const mobileSrc = getScreenshotUrl(data?.screenshots?.mobile);

console.log("📥 Desktop source:", desktopSrc ? `${desktopSrc.substring(0, 50)}...` : "NOT FOUND");
"@
    
    # Replace
    $newContent = $content -replace $oldPattern, $replacement
    
    # Backup original
    $backupPath = "$filePath.backup"
    Copy-Item $filePath $backupPath
    Write-Host "💾 Backup created: $backupPath" -ForegroundColor Yellow
    
    # Write new content
    Set-Content $filePath -Value $newContent -NoNewline
    
    Write-Host "✅ File patched successfully!" -ForegroundColor Green
    Write-Host "📋 Changes:" -ForegroundColor Cyan
    Write-Host "  - Added getScreenshotUrl helper function" -ForegroundColor White
    Write-Host "  - Updated desktopSrc extraction to use new schema" -ForegroundColor White
    Write-Host "  - Updated mobileSrc extraction to use new schema" -ForegroundColor White
} else {
    Write-Host "⚠️ Could not find exact pattern to patch." -ForegroundColor Yellow
    Write-Host "Please manually update the file using FRONTEND_PATCH.md" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n✅ Done! The frontend should now work with the new screenshot schema." -ForegroundColor Green


