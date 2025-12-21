# PowerShell script to test image-trust endpoint

$apiUrl = "http://127.0.0.1:8000/api/analyze/image-trust?debug=1"

# Get test image path - try common test images
$testImages = @("test_image.jpg", "test.jpg", "url_test.png")

$f = $null
foreach ($img in $testImages) {
    if (Test-Path $img) {
        $f = $img
        break
    }
}

if (-not $f) {
    Write-Host "❌ No test image found. Please provide an image file path." -ForegroundColor Red
    Write-Host "Looking for: $($testImages -join ', ')" -ForegroundColor Yellow
    exit 1
}

Write-Host "Testing image-trust endpoint..." -ForegroundColor Cyan
Write-Host "Image file: $f" -ForegroundColor Cyan
Write-Host "URL: $apiUrl" -ForegroundColor Cyan
Write-Host ""

try {
    $response = curl.exe -s -X POST -F "file=@$f" $apiUrl | Out-String
    
    Write-Host "✅ SUCCESS!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Response:" -ForegroundColor Cyan
    
    # Try to format as JSON if possible
    try {
        $jsonResponse = $response | ConvertFrom-Json
        $jsonResponse | ConvertTo-Json -Depth 10
    } catch {
        Write-Host $response
    }
} catch {
    Write-Host "❌ ERROR:" -ForegroundColor Red
    Write-Host $_.Exception.Message
    if ($_.ErrorDetails.Message) {
        Write-Host $_.ErrorDetails.Message
    }
}












