# NataliaBot Backup
$src = "C:\NataliaBot"
$dst = "C:\NataliaBot_Backup_$(Get-Date -Format 'yyyyMMdd_HHmm')"
Copy-Item -Recurse -Path $src -Destination $dst -Exclude @(".venv","__pycache__","*.pyc")
Write-Host "Backup erstellt: $dst" -ForegroundColor Green
