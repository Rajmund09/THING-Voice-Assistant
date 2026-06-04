# setup_ollama.ps1
# Automated installer for Ollama and local LLM for THING Edge-AI

Write-Host "========================================"
Write-Host "   THING v5.5 Edge-AI Setup (Windows)   "
Write-Host "========================================"

# Check if Ollama is already installed
if (Get-Command ollama -ErrorAction SilentlyContinue) {
    Write-Host "✅ Ollama is already installed."
} else {
    Write-Host "⏳ Downloading Ollama installer..."
    $installerPath = "$env:TEMP\OllamaSetup.exe"
    Invoke-WebRequest -Uri "https://ollama.com/download/OllamaSetup.exe" -OutFile $installerPath
    
    if (Test-Path $installerPath) {
        Write-Host "⏳ Installing Ollama. Please follow the prompts..."
        Start-Process -FilePath $installerPath -Wait
        Remove-Item $installerPath
        Write-Host "✅ Ollama installation finished. Please make sure it's running."
    } else {
        Write-Host "❌ Failed to download Ollama installer."
        exit
    }
}

# Pull the default local model
$MODEL = "phi3:mini"
Write-Host "⏳ Pulling local model: $MODEL (This may take a few minutes)..."
ollama pull $MODEL

if ($?) {
    Write-Host "========================================"
    Write-Host "✅ Setup Complete! Local AI is ready."
    Write-Host "THING will now use $MODEL when offline."
    Write-Host "========================================"
} else {
    Write-Host "❌ Failed to pull the model. Is Ollama running?"
}
