# Fixed version of your command
# This script handles image upload to /api/analyze/image-human

# Set BASE URL (this was missing in your original command)
$BASE = "http://127.0.0.1:8000"

# Your image_id
$imageId = "9f1c1f0c-e742-426f-9fba-43e918267e9a.png"

# Try to find the image file in common locations
$possiblePaths = @(
    "api\artifacts\$imageId",
    "api\artifacts\$imageId",
    ".\$imageId",
    "..\$imageId"
)

$imagePath = $null
foreach ($path in $possiblePaths) {
    if (Test-Path $path) {
        $imagePath = $path
        Write-Host "Found image at: $imagePath" -ForegroundColor Green
        break
    }
}

if (-not $imagePath) {
    Write-Host "Image file not found with ID: $imageId" -ForegroundColor Red
    Write-Host "Please provide the full path to the image file:" -ForegroundColor Yellow
    Write-Host "  `$imagePath = 'full\path\to\$imageId'" -ForegroundColor Cyan
    exit 1
}

# Goal
$goal = "leads"

Write-Host "`nUploading image to: $BASE/api/analyze/image-human" -ForegroundColor Cyan
Write-Host "Image: $imagePath" -ForegroundColor Cyan
Write-Host "Goal: $goal" -ForegroundColor Cyan
Write-Host ""

try {
    # Read image file as bytes
    $imageBytes = [System.IO.File]::ReadAllBytes((Resolve-Path $imagePath))
    $fileName = Split-Path -Leaf $imagePath
    
    # Create boundary for multipart form data
    $boundary = [System.Guid]::NewGuid().ToString()
    $LF = "`r`n"
    
    # Build multipart form data body
    $bodyLines = @(
        "--$boundary",
        "Content-Disposition: form-data; name=`"image`"; filename=`"$fileName`"",
        "Content-Type: image/png",
        "",
        [System.Text.Encoding]::GetEncoding("iso-8859-1").GetString($imageBytes),
        "--$boundary",
        "Content-Disposition: form-data; name=`"goal`"",
        "",
        $goal,
        "--$boundary--"
    )
    
    $body = $bodyLines -join $LF
    $bodyBytes = [System.Text.Encoding]::GetEncoding("iso-8859-1").GetBytes($body)
    
    # Create request
    $uri = "$BASE/api/analyze/image-human"
    $headers = @{
        "Content-Type" = "multipart/form-data; boundary=$boundary"
    }
    
    # Send request (this replaces your original Invoke-RestMethod call)
    $r = Invoke-RestMethod -Uri $uri `
        -Method POST `
        -Headers $headers `
        -Body $bodyBytes
    
    Write-Host "✅ Success!" -ForegroundColor Green
    Write-Host "`nResponse:" -ForegroundColor Cyan
    $r | ConvertTo-Json -Depth 10
    
} catch {
    Write-Host "`n❌ Error occurred:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    if ($_.ErrorDetails.Message) {
        Write-Host "Details:" -ForegroundColor Yellow
        Write-Host $_.ErrorDetails.Message -ForegroundColor Yellow
    }
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "Response body:" -ForegroundColor Yellow
        Write-Host $responseBody -ForegroundColor Yellow
    }
}



