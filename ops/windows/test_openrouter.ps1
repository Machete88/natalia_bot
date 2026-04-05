# OpenRouter API testen
$env_file = "C:\NataliaBot\.env"
$key = (Get-Content $env_file | Where-Object { $_ -match "^OPENAI_API_KEY=" }) -replace "OPENAI_API_KEY=", ""
$model = (Get-Content $env_file | Where-Object { $_ -match "^LLM_MODEL=" }) -replace "LLM_MODEL=", ""

Write-Host "Teste OpenRouter mit Modell: $model" -ForegroundColor Cyan

$body = @{
    model = $model
    messages = @(@{ role = "user"; content = "Say: API test OK" })
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "https://openrouter.ai/api/v1/chat/completions" `
    -Method Post `
    -Headers @{ Authorization = "Bearer $key"; "Content-Type" = "application/json" } `
    -Body $body

Write-Host "Antwort: $($response.choices[0].message.content)" -ForegroundColor Green
