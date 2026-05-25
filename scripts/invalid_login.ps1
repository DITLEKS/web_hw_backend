$ErrorActionPreference = 'Stop'
try {
    $r = Invoke-RestMethod -Uri 'http://localhost:3002/api/v1/auth/login' -Method Post -ContentType 'application/json' -Body (ConvertTo-Json @{email='admin@smartlight.ru'; password='wrong'})
    Write-Output ($r | ConvertTo-Json -Compress)
} catch {
    $resp = $_.Exception.Response
    if ($resp -ne $null) {
        $sr = New-Object System.IO.StreamReader($resp.GetResponseStream())
        Write-Output ($sr.ReadToEnd())
    } else {
        Write-Output ($_ | ConvertTo-Json -Compress)
    }
}
