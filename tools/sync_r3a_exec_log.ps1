param(
    [int]$MaxRetries = 3,
    [string]$Remote = "origin",
    [string]$Branch = "main"
)

$ErrorActionPreference = "Stop"

function Invoke-Git {
    param([Parameter(Mandatory = $true)][string[]]$Args)
    & git @Args
    if ($LASTEXITCODE -ne 0) {
        throw "git $($Args -join ' ') failed with exit code $LASTEXITCODE"
    }
}

function Get-Head {
    (& git rev-parse HEAD).Trim()
}

function Get-RemoteHead {
    $line = (& git ls-remote $Remote "refs/heads/$Branch")
    if ($LASTEXITCODE -ne 0 -or -not $line) {
        throw "Unable to read remote head for $Remote/$Branch"
    }
    return ($line -split "\s+")[0]
}

Invoke-Git @("rev-parse", "--show-toplevel") | Out-Null
$status = (& git status --short)
if ($status) {
    Write-Host "Working tree has changes:"
    $status | ForEach-Object { Write-Host $_ }
}

for ($attempt = 1; $attempt -le $MaxRetries; $attempt++) {
    try {
        Write-Host "Sync attempt $attempt/$MaxRetries"
        Invoke-Git @("fetch", $Remote, $Branch)
        Invoke-Git @("rebase", "$Remote/$Branch")
        Invoke-Git @("push", $Remote, $Branch)

        $localHead = Get-Head
        $remoteHead = Get-RemoteHead
        if ($localHead -ne $remoteHead) {
            throw "Remote head verification failed: local=$localHead remote=$remoteHead"
        }
        Write-Host "Push verified: $remoteHead"
        exit 0
    }
    catch {
        Write-Host "Sync attempt $attempt failed: $($_.Exception.Message)"
        if ($attempt -eq $MaxRetries) {
            throw
        }
        $sleepSeconds = @(10, 30, 60)[$attempt - 1]
        Write-Host "Retrying in $sleepSeconds seconds..."
        Start-Sleep -Seconds $sleepSeconds
    }
}
