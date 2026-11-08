$launcher = Join-Path $PSScriptRoot 'OPEN_TRACKER.pyw'
Start-Process -FilePath (Get-Command pythonw.exe -ErrorAction Stop).Source -ArgumentList ('"' + $launcher + '"') -WindowStyle Hidden
