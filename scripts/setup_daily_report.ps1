# Windows Task Scheduler Registration Script
# Register daily portfolio report generation task

$TaskName = "PortfolioDailyReport"
$ScriptPath = Join-Path $PSScriptRoot "generate_report_with_cursor.ps1"
$ProjectPath = "C:\Users\iamyo\wewake_portfolio"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Portfolio Report Auto-Generation Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Check if task already exists
$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host ""
    Write-Host "Existing task found. Removing..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Create task action (chcp 65001으로 UTF-8 설정 후 PowerShell 실행 → 한글 로그 정상 표시)
$action = New-ScheduledTaskAction -Execute "cmd.exe" `
    -Argument "/c chcp 65001 >nul && powershell.exe -ExecutionPolicy Bypass -NoProfile -File `"$ScriptPath`" -ProjectPath `"$ProjectPath`""

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
    Write-Host "Task registered successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Task Information:" -ForegroundColor Cyan
    Write-Host "  Task Name: $TaskName" -ForegroundColor White
    Write-Host "  Execution Time: Daily at 8:00 AM" -ForegroundColor White
    Write-Host "  Script: $ScriptPath" -ForegroundColor White
    
    Write-Host ""
    Write-Host "Check task:" -ForegroundColor Yellow
    Write-Host "  Get-ScheduledTask -TaskName $TaskName" -ForegroundColor Gray
    
    Write-Host ""
    Write-Host "Delete task:" -ForegroundColor Yellow
    Write-Host "  Unregister-ScheduledTask -TaskName $TaskName -Confirm:`$false" -ForegroundColor Gray
    
    Write-Host ""
    Write-Host "Manual run:" -ForegroundColor Yellow
    Write-Host "  Start-ScheduledTask -TaskName $TaskName" -ForegroundColor Gray
    
} catch {
    Write-Host ""
    Write-Host "Error: Task registration failed" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
