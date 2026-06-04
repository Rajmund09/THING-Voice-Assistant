#!/bin/bash
# setup_ollama.sh
# Automated installer for Ollama and local LLM for THING Edge-AI

echo "========================================"
echo "   THING v5.5 Edge-AI Setup (macOS/Linux) "
echo "========================================"

# Check if curl is installed
if ! command -v curl &> /dev/null; then
    echo "❌ curl could not be found. Please install curl first."
    exit 1
fi

# Check if Ollama is already installed
if ! command -v ollama &> /dev/null; then
    echo "⏳ Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install Ollama."
        exit 1
    fi
else
    echo "✅ Ollama is already installed."
fi

# Ensure Ollama server is running in the background
echo "⏳ Starting Ollama server in background..."
ollama serve > /dev/null 2>&1 &
sleep 3

# Pull the default local model
# We use phi3:mini as it is fast and small (2.3GB), perfect for intent classification.
MODEL="phi3:mini"
echo "⏳ Pulling local model: $MODEL (This may take a few minutes)..."
ollama pull $MODEL

if [ $? -eq 0 ]; then
    echo "========================================"
    echo "✅ Setup Complete! Local AI is ready."
    echo "THING will now use $MODEL when offline."
    echo "========================================"
else
    echo "❌ Failed to pull the model."
    exit 1
fi
