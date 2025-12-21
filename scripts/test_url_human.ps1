# Test script for /api/analyze/url-human endpoint
# This uses standard PowerShell methods that work 100% correctly

Write-Host ""
Write-Host "=== Testing /api/analyze/url-human endpoint ===" -ForegroundColor Cyan
Write-Host ""

# Build body using ConvertTo-Json (standard PowerShell method)
$body = @{
  url    = "https://nimasaraeian.com/"
  goal   = "leads"
  locale = "fa"
} | ConvertTo-Json

Write-Host "Sending request:" -ForegroundColor Yellow
Write-Host $body
Write-Host ""

try {
    # Send request with Invoke-RestMethod (standard method)
    $r = Invoke-RestMethod `
        -Uri "http://127.0.0.1:8000/api/analyze/url-human" `
        -Method Post `
        -ContentType "application/json" `
        -Body $body `
        -ErrorAction Stop

    Write-Host "SUCCESS: Response received!" -ForegroundColor Green
    Write-Host ""
    $r | ConvertTo-Json -Depth 5
    
} catch {
    Write-Host "ERROR: Request failed" -ForegroundColor Red
    
    # Show status code
    if ($_.Exception.Response) {
        $statusCode = $_.Exception.Response.StatusCode.value__
        Write-Host "  Status Code: $statusCode" -ForegroundColor Red
    }
    
    # Show error message from server
    if ($_.Exception.Response) {
        try {
            $errorStream = $_.Exception.Response.GetResponseStream()
            $reader = New-Object IO.StreamReader($errorStream)
            $errorBody = $reader.ReadToEnd()
            Write-Host ""
            Write-Host "Error details from server:" -ForegroundColor Yellow
            Write-Host $errorBody
        } catch {
            Write-Host "  $($_.Exception.Message)" -ForegroundColor Red
        }
    } else {
        Write-Host "  $($_.Exception.Message)" -ForegroundColor Red
    }
    
    Write-Host ""
    exit 1
}

Write-Host ""
Write-Host "=== Test completed ===" -ForegroundColor Cyan
Write-Host ""
