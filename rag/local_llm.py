import subprocess
import json
import os
from pathlib import Path

def run_local_llm(prompt, model="llama3.2"):
    # Try to find ollama executable on Windows if not in PATH
    ollama_path = "ollama"
    if os.name == 'nt':
        default_path = Path(os.environ.get('LOCALAPPDATA', '')) / "Programs" / "Ollama" / "ollama.exe"
        if default_path.exists():
            ollama_path = str(default_path)

    # Using subprocess to call ollama CLI
    cmd = [ollama_path, "run", model, prompt]
    try:
        # Prevent hanging by adding timeout if needed
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30)
        if result.returncode != 0:
            return f"Error calling Ollama: {result.stderr}"
        return result.stdout.strip()
    except FileNotFoundError:
        return "Error: Ollama executable not found. Please ensure Ollama is installed and in your PATH."
    except subprocess.TimeoutExpired:
        return "Error: Ollama call timed out."
    except Exception as e:
        return f"Exception calling Ollama: {str(e)}"
