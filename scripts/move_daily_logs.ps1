# 기존 report/daily_*.log 파일들을 해당 리포트 디렉토리(report/YYYYMMDD_HHmm/)로 이동
param(
    [string]$ProjectPath = "C:\Users\iamyo\wewake_portfolio"
)

$reportDir = Join-Path $ProjectPath "report"
$logs = Get-ChildItem -Path $reportDir -Filter "daily_*.log" -File -ErrorAction SilentlyContinue
if (-not $logs) {
    Write-Host "No daily_*.log files found." -ForegroundColor Gray
    exit 0
}

$dirs = Get-ChildItem -Path $reportDir -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^\d{8}_\d{4}$' }

foreach ($log in $logs) {
    if ($log.Name -match '^daily_(\d{8})_(\d{2})(\d{2})(\d{2})\.log$') {
        $datePart = $matches[1]
        $hh = $matches[2]
        $mm = $matches[3]
        $ss = $matches[4]
        $logHhmm = $hh + $mm
        $targetDirName = "${datePart}_${logHhmm}"
        $targetDir = Join-Path $reportDir $targetDirName

        $moved = $false
        if (Test-Path $targetDir) {
            Move-Item -Path $log.FullName -Destination (Join-Path $targetDir $log.Name) -Force
            Write-Host "Moved $($log.Name) -> $targetDirName/" -ForegroundColor Green
            $moved = $true
        } else {
            $sameDateDirs = $dirs | Where-Object { $_.Name.StartsWith("${datePart}_") } | Sort-Object Name
            if ($sameDateDirs) {
                $logMinutes = [int]$hh * 60 + [int]$mm
                $closest = $sameDateDirs | ForEach-Object {
                    if ($_.Name -match '_(\d{2})(\d{2})$') {
                        $dMinutes = [int]$matches[1] * 60 + [int]$matches[2]
                        [PSCustomObject]@{ Dir = $_; Diff = [Math]::Abs($logMinutes - $dMinutes) }
                    }
                } | Sort-Object Diff | Select-Object -First 1
                if ($closest) {
                    $dest = Join-Path $closest.Dir.FullName $log.Name
                    Move-Item -Path $log.FullName -Destination $dest -Force
                    Write-Host "Moved $($log.Name) -> $($closest.Dir.Name)/ (closest match)" -ForegroundColor Green
                    $moved = $true
                }
            }
        }
        if (-not $moved) {
            New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
            Move-Item -Path $log.FullName -Destination (Join-Path $targetDir $log.Name) -Force
            Write-Host "Moved $($log.Name) -> $targetDirName/ (created)" -ForegroundColor Yellow
        }
    }
}
Write-Host "Done." -ForegroundColor Cyan
