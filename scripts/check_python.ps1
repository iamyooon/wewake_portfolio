# Python Installation Check Script

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Python Installation Check" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$pythonFound = $false
$pythonPath = $null

# Method 1: Search in PATH
Write-Host ""
Write-Host "1. Searching Python in PATH..." -ForegroundColor Yellow
$python = Get-Command python -ErrorAction SilentlyContinue
if ($python) {
    $pythonPath = $python.Source
    $pythonFound = $true
    Write-Host "   Found: $pythonPath" -ForegroundColor Green
} else {
    Write-Host "   Not found in PATH" -ForegroundColor Red
}

# Method 2: Search common installation locations
if (-not $pythonFound) {
    Write-Host ""
    Write-Host "2. Searching common installation locations..." -ForegroundColor Yellow
    $commonPaths = @(
        "$env:LOCALAPPDATA\Programs\Python\Python*",
        "$env:ProgramFiles\Python*",
        "$env:ProgramFiles(x86)\Python*",
        "C:\Python*"
    )
    
    foreach ($pathPattern in $commonPaths) {
        $pythonDirs = Get-ChildItem $pathPattern -Directory -ErrorAction SilentlyContinue
        foreach ($dir in $pythonDirs) {
            $pythonExe = Join-Path $dir.FullName "python.exe"
            if (Test-Path $pythonExe) {
                $pythonPath = $pythonExe
                $pythonFound = $true
                Write-Host "   Found: $pythonExe" -ForegroundColor Green
                break
            }
        }
        if ($pythonFound) { break }
    }
    
    if (-not $pythonFound) {
        Write-Host "   Not found in common locations" -ForegroundColor Red
    }
}

# Output result
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
if ($pythonFound) {
    Write-Host "Python installation found" -ForegroundColor Green
    Write-Host "   Path: $pythonPath" -ForegroundColor White
    
    # Check Python version
    Write-Host ""
    Write-Host "Python version:" -ForegroundColor Yellow
    & $pythonPath --version
    
    # Check pip
    Write-Host ""
    Write-Host "pip check:" -ForegroundColor Yellow
    $pipPath = Join-Path (Split-Path $pythonPath) "Scripts\pip.exe"
    if (Test-Path $pipPath) {
        Write-Host "   pip found: $pipPath" -ForegroundColor Green
        & $pipPath --version
    } else {
        Write-Host "   pip not found" -ForegroundColor Yellow
    }
} else {
    Write-Host "Python is not installed" -ForegroundColor Red
    Write-Host ""
    Write-Host "Installation guide:" -ForegroundColor Yellow
    Write-Host "1. Visit https://www.python.org/downloads/" -ForegroundColor White
    Write-Host "2. Download and install latest Python" -ForegroundColor White
    Write-Host "3. Check 'Add Python to PATH' during installation" -ForegroundColor White
    Write-Host ""
    Write-Host "Or install from Microsoft Store: search 'Python'" -ForegroundColor White
}
Write-Host "========================================" -ForegroundColor Cyan
