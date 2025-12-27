# PowerShell script to test /api/analyze/image-human endpoint
# This endpoint requires multipart/form-data with file upload

$BASE = "http://127.0.0.1:8000"

# Option 1: If you have the image file path
$imagePath = "path\to\your\image.png"  # Replace with actual image path

# Option 2: If image is in artifacts directory, use one of the existing files
# $imagePath = "api\artifacts\atf_desktop_1766482842.png"

# Check if file exists
if (-not (Test-Path $imagePath)) {
    Write-Host "Error: Image file not found at: $imagePath" -ForegroundColor Red
    Write-Host "Please update `$imagePath with the correct path to your image file." -ForegroundColor Yellow
    exit 1
}

Write-Host "Uploading image: $imagePath" -ForegroundColor Cyan
Write-Host "Endpoint: $BASE/api/analyze/image-human" -ForegroundColor Cyan
Write-Host "Goal: leads" -ForegroundColor Cyan
Write-Host ""

try {
    # Create multipart form data
    $form = @{
        image = Get-Item -Path $imagePath
        goal = "leads"
    }
    
    # Send request
    $response = Invoke-RestMethod -Uri "$BASE/api/analyze/image-human" `
        -Method POST `
        -Form $form `
        -ContentType "multipart/form-data"
    
    Write-Host "✅ Success!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Response:" -ForegroundColor Cyan
    $response | ConvertTo-Json -Depth 10
    
} catch {
    Write-Host "❌ Error occurred:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    if ($_.ErrorDetails.Message) {
        Write-Host "Details: $($_.ErrorDetails.Message)" -ForegroundColor Yellow
    }
}
