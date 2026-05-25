$ErrorActionPreference = 'Stop'
$login = Invoke-RestMethod -Uri 'http://localhost:3002/api/v1/auth/login' -Method Post -ContentType 'application/json' -Body (ConvertTo-Json @{email='admin@smartlight.ru'; password='AdminPass123!'})
Write-Output '---LOGIN---'
Write-Output ($login | ConvertTo-Json -Compress)
$refresh = Invoke-RestMethod -Uri 'http://localhost:3002/api/v1/auth/refresh' -Method Post -ContentType 'application/json' -Body (ConvertTo-Json @{refresh_token=$login.data.refresh_token})
Write-Output '---REFRESH---'
Write-Output ($refresh | ConvertTo-Json -Compress)
$dashboard = Invoke-RestMethod -Uri 'http://localhost:3002/api/v1/dashboard' -Headers @{Authorization = 'Bearer ' + $login.data.access_token}
Write-Output '---DASHBOARD---'
Write-Output ($dashboard | ConvertTo-Json -Compress)
