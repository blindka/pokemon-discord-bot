# start.ps1 - Start bot safely (kills existing instances first)
# Run with: .\start.ps1

Write-Host "Searching for existing bot instances..." -ForegroundColor Cyan

$killed = 0
$allProcs = Get-WmiObject Win32_Process
foreach ($proc in $allProcs) {
    if ($proc.Name -like "python*") {
        $cmdLine = $proc.CommandLine
        if ($cmdLine -like "*bot.py*") {
            $procPid = $proc.ProcessId
            Write-Host "Killing process PID $procPid..." -ForegroundColor Yellow
            Stop-Process -Id $procPid -Force -ErrorAction SilentlyContinue
            $killed++
        }
    }
}

if ($killed -gt 0) {
    Write-Host "Killed $killed old instance(s)." -ForegroundColor Green
    Start-Sleep -Milliseconds 800
} else {
    Write-Host "No existing instances found." -ForegroundColor Green
}

if (Test-Path "bot.pid") {
    Remove-Item "bot.pid" -Force
    Write-Host "Deleted stale PID file." -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "Starting bot..." -ForegroundColor Green
Write-Host "------------------------------" -ForegroundColor DarkGray
python bot.py
