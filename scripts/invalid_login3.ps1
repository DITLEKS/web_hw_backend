try {
    $r = Invoke-WebRequest -Uri 'http://localhost:3002/api/v1/auth/login' -Method Post -ContentType 'application/json' -Body (ConvertTo-Json @{email='admin@smartlight.ru'; password='wrong'}) -ErrorAction Stop
    Write-Output "StatusCode: $($r.StatusCode.Value__)"
    Write-Output "Content: $($r.Content)"
} catch {
    $resp = $_.Exception.Response
    $sr = New-Object System.IO.StreamReader($resp.GetResponseStream())
    $body = $sr.ReadToEnd()
    Write-Output "StatusCode: $($resp.StatusCode.Value__)"
    Write-Output "Content: $body"
}
