# Ensure Ollama model is available. Run: .\scripts\ensure-ollama-model.ps1
$model = if ($env:OLLAMA_MODEL) { $env:OLLAMA_MODEL } else { "tinyllama" }
Write-Host "Ensuring Ollama model: $model"
$list = ollama list 2>&1 | Out-String
if ($list -notmatch [regex]::Escape($model.Split(":")[0])) {
    ollama pull $model
} else {
    Write-Host "Model $model already present."
}
