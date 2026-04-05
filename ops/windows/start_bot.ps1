# NataliaBot starten
$ProjectDir = "C:\NataliaBot"
cd $ProjectDir
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"
& "$ProjectDir\.venv\Scripts\python" -m app.main
