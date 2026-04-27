Write-Host "🚀 Launching Dynamic Pricing Engine Demo..." -ForegroundColor Cyan

$venv = ".\venv\Scripts\python.exe"
$streamlit = ".\venv\Scripts\streamlit.exe"

# 1. Start Data Simulator
Write-Host "1. Starting Data Simulator..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "$venv simulate_data.py"

# 2. Start WebSocket Server
Write-Host "2. Starting WebSocket Server..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "$venv ws_server.py"

# 3. Start Pathway Pipeline
Write-Host "3. Starting Pathway Pipeline..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "$venv pathway_pipeline.py"

# 4. Start Streamlit Dashboard
Write-Host "4. Starting Dashboard..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "$streamlit run app.py"

Write-Host "✅ All systems go! Check the new windows." -ForegroundColor Cyan
