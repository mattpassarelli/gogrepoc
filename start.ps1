# Enable running multiple commands simultaneously
$ErrorActionPreference = "Stop"

# Function to print colorful messages
function Write-Colored($message, $color) {
    Write-Host $message -ForegroundColor $color
}

Write-Colored "🚀 Starting GOG Repo Manager..." "Cyan"

# Check if Python is installed
try {
    python --version
} catch {
    Write-Colored "❌ Python 3 is not installed. Please install Python 3 and try again." "Red"
    exit 1
}

# Check if Node.js is installed
try {
    node --version
} catch {
    Write-Colored "❌ Node.js is not installed. Please install Node.js and try again." "Red"
    exit 1
}

# Create virtual environment if it doesn't exist
if (-not (Test-Path "venv")) {
    Write-Colored "📦 Creating Python virtual environment..." "Cyan"
    python -m venv venv
}

# Activate virtual environment
Write-Colored "🔄 Activating virtual environment..." "Cyan"
. .\venv\Scripts\Activate.ps1

# Install Python requirements
Write-Colored "📥 Installing Python dependencies..." "Cyan"
pip install -r requirements.txt

# Install npm dependencies and build the UI
Write-Colored "🌐 Setting up web interface..." "Cyan"
Set-Location ui
npm install
npm run build
Set-Location ..

# Start both servers
Write-Colored "✨ Starting servers..." "Green"
Write-Colored "🔗 Web interface will be available at: http://localhost:3000" "Green"

# Start both servers in separate jobs
$uvicornJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    . .\venv\Scripts\Activate.ps1
    uvicorn main:app --host 0.0.0.0 --port 8000
}

$uiJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    . .\venv\Scripts\Activate.ps1
    Set-Location ui
    python -m http.server 3000 --directory build
}

# Handle script termination
try {
    while ($true) {
        Start-Sleep -Seconds 1
        # Check if either job has failed
        if ($uvicornJob.State -eq "Failed" -or $uiJob.State -eq "Failed") {
            throw "One of the servers has stopped unexpectedly"
        }
    }
} finally {
    # Clean up jobs when the script is terminated
    Stop-Job -Job $uvicornJob, $uiJob
    Remove-Job -Job $uvicornJob, $uiJob
}
