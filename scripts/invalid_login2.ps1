$r = Invoke-WebRequest -Uri 'http://localhost:3002/api/v1/auth/login' -Method Post -ContentType 'application/json' -Body (ConvertTo-Json @{email='admin@smartlight.ru'; password='wrong'}) -ErrorAction SilentlyContinue
Write-Output 'StatusCode:';$r.StatusCode.Value__
Write-Output 'Content:';$r.Content
