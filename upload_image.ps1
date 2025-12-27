# PowerShell 5.1 compatible image upload script
# For /api/analyze/image-human endpoint

$BASE = "http://127.0.0.1:8000"

# Set image path - replace with your actual image path
$imagePath = "api\artifacts\atf_desktop_1766482842.png"

# Check if file exists
if (-not (Test-Path $imagePath)) {
    Write-Host "Error: Image file not found at: $imagePath" -ForegroundColor Red
    exit 1
}

Write-Host "Uploading image: $imagePath" -ForegroundColor Cyan
Write-Host "Endpoint: $BASE/api/analyze/image-human" -ForegroundColor Cyan

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
        "leads",
        "--$boundary--"
    )
    
    $body = $bodyLines -join $LF
    $bodyBytes = [System.Text.Encoding]::GetEncoding("iso-8859-1").GetBytes($body)
    
    # Create request
    $uri = "$BASE/api/analyze/image-human"
    $headers = @{
        "Content-Type" = "multipart/form-data; boundary=$boundary"
    }
    
    # Send request
    $response = Invoke-RestMethod -Uri $uri `
        -Method POST `
        -Headers $headers `
        -Body $bodyBytes
    
    Write-Host "`n✅ Success!" -ForegroundColor Green
    Write-Host "`nResponse:" -ForegroundColor Cyan
    $response | ConvertTo-Json -Depth 10
    
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


