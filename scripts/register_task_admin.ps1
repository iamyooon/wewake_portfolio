# Run this script as Administrator
# Right-click PowerShell and select "Run as Administrator"

$TaskName = "PortfolioDailyReport"
$ScriptPath = "C:\Users\iamyo\wewake_portfolio\scripts\generate_report_with_cursor.ps1"
$ProjectPath = "C:\Users\iamyo\wewake_portfolio"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Portfolio Report Auto-Generation Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host ""
    Write-Host "ERROR: This script must be run as Administrator" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please:" -ForegroundColor Yellow
    Write-Host "1. Right-click PowerShell" -ForegroundColor White
    Write-Host "2. Select 'Run as Administrator'" -ForegroundColor White
    Write-Host "3. Run this script again" -ForegroundColor White
    exit 1
}

# Check if task already exists
$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host ""
    Write-Host "Existing task found. Removing..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Create task action
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" `
    -Argument "-ExecutionPolicy Bypass -File `"$ScriptPath`" -ProjectPath `"$ProjectPath`""

# Create trigger (daily at 8:00 AM)
$trigger = New-ScheduledTaskTrigger -Daily -At "08:00"

# Create settings
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable

# Register task
try {
    Register-ScheduledTask -TaskName $TaskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Description "Generate portfolio report daily at 8:00 AM" `
        -RunLevel Highest
    
    Write-Host ""
    Write-Host "SUCCESS: Task registered!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Task Information:" -ForegroundColor Cyan
    Write-Host "  Task Name: $TaskName" -ForegroundColor White
    Write-Host "  Execution Time: Daily at 8:00 AM" -ForegroundColor White
    Write-Host "  Script: $ScriptPath" -ForegroundColor White
    
    Write-Host ""
    Write-Host "To check task:" -ForegroundColor Yellow
    Write-Host "  Get-ScheduledTask -TaskName $TaskName" -ForegroundColor Gray
    
    Write-Host ""
    Write-Host "To delete task:" -ForegroundColor Yellow
    Write-Host "  Unregister-ScheduledTask -TaskName $TaskName -Confirm:`$false" -ForegroundColor Gray
    
    Write-Host ""
    Write-Host "To run manually:" -ForegroundColor Yellow
    Write-Host "  Start-ScheduledTask -TaskName $TaskName" -ForegroundColor Gray
    
} catch {
    Write-Host ""
    Write-Host "ERROR: Task registration failed" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
