<#
PowerShell helper: free port 8080 by terminating owning process(es).
Usage: Run in PowerShell as Administrator: .\scripts\free_ports.ps1
#>
try {
    Write-Host "Checking for processes owning TCP port 8080..."
    $conns = @()
    if (Get-Command -Name Get-NetTCPConnection -ErrorAction SilentlyContinue) {
        $conns = Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue
    } else {
        $raw = netstat -ano -p tcp | Select-String ":8080"
        foreach ($line in $raw) { $conns += $line.ToString() }
    }

    if (-not $conns -or $conns.Count -eq 0) {
        Write-Host "No process found listening on port 8080."
        exit 0
    }

    # If we have Get-NetTCPConnection objects, stop processes by OwningProcess
    foreach ($c in $conns) {
        if ($c -is [System.String]) {
            # netstat fallback parsing
            if ($c -match "\s+(\d+)$") { $pid = $Matches[1] } else { continue }
        } else {
            $pid = $c.OwningProcess
        }
        try {
            Write-Host "Attempting to stop PID $pid (port 8080 owner)..."
            Stop-Process -Id $pid -Force -ErrorAction Stop
            Write-Host "Stopped PID $pid"
        } catch {
            Write-Warning "Failed to stop PID $pid via Stop-Process; trying taskkill..."
            cmd.exe /c "taskkill /F /PID $pid" | Out-Null
        }
    }

    # Optional aggressive fallback: kill lingering python.exe processes that may be orphaned
    Write-Host "Running safer python.exe sweep for common uvicorn windows titles (non-aggressive)..."
    try {
        # This tries to target python processes whose window title mentions uvicorn
        cmd.exe /c 'tasklist /V /FI "IMAGENAME eq python.exe"' | Select-String -Pattern "uvicorn" | ForEach-Object {
            $line = $_.ToString()
            if ($line -match "\s+(\d+)\s+") { $pid = $Matches[1]; cmd.exe /c "taskkill /F /PID $pid" | Out-Null; Write-Host "Killed python.exe PID $pid (uvicorn)" }
        }
    } catch {
        Write-Warning "Python sweep failed: $_"
    }

    Write-Host "Port 8080 remediation complete."
    exit 0
} catch {
    Write-Error "Free-ports script encountered an error: $_"
    exit 1
}
