$lines = netstat -ano | findstr :8000
$lines | % { ($_ -split "\s+")[-1] } | Select-Object -Unique | % { taskkill /PID $_ /F }
