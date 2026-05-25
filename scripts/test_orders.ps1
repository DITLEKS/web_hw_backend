$ErrorActionPreference = 'Stop'
$login = Invoke-RestMethod -Uri 'http://localhost:3002/api/v1/auth/login' -Method Post -ContentType 'application/json' -Body (ConvertTo-Json @{email='admin@smartlight.ru'; password='AdminPass123!'})
Write-Output '---ORDERS_LIST---'
$orders = Invoke-RestMethod -Uri 'http://localhost:3002/api/v1/orders?page=1&limit=20' -Headers @{Authorization='Bearer ' + $login.data.access_token}
Write-Output ($orders | ConvertTo-Json -Compress)
Write-Output '---ORDER_DETAIL---'
$detail = Invoke-RestMethod -Uri 'http://localhost:3002/api/v1/orders/LX-20260525-0001' -Headers @{Authorization='Bearer ' + $login.data.access_token}
Write-Output ($detail | ConvertTo-Json -Compress)
Write-Output '---INVALID_STATUS_UPDATE---'
try {
    $resp = Invoke-RestMethod -Uri 'http://localhost:3002/api/v1/orders/LX-20260525-0001/status' -Method Patch -ContentType 'application/json' -Headers @{Authorization='Bearer ' + $login.data.access_token} -Body (ConvertTo-Json @{status='delivered'; tracking_number=$null; comment='skip steps'})
    Write-Output ($resp | ConvertTo-Json -Compress)
} catch {
    $r = $_.Exception.Response
    if ($r -ne $null) {
        $stream = $r.GetResponseStream()
        $reader = New-Object System.IO.StreamReader($stream)
        $body = $reader.ReadToEnd()
        Write-Output $body
    } else {
        Write-Output ($_ | ConvertTo-Json -Compress)
    }
}
