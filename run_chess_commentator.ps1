# Check if venv exists, create if it doesn't
if (-not (Test-Path ".\venv")) {
    Write-Host "Creating virtual environment..."
    python -m venv venv
}

# Activate virtual environment
Write-Host "Activating virtual environment..."
.\venv\Scripts\Activate.ps1

# Install requirements if needed
if (-not (Test-Path ".\venv\Lib\site-packages\pygame")) {
    Write-Host "Installing requirements..."
    pip install -r requirements.txt
}

# Run the program
Write-Host "Running Chess Commentator..."
python main.py

# Deactivate virtual environment
deactivate 