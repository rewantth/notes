# Run this yourself in PowerShell, inside this folder:   .\set-secrets.ps1
# It uploads the 3 Gmail values from github-secrets.txt to the GitHub repo's encrypted Secrets
# and asks you to type the passphrase that unlocks your dashboard.
# Nothing is printed and nothing is sent anywhere except GitHub's encrypted secret store.
#
# Usage:
#   .\set-secrets.ps1                    first-time setup (uses the repo this folder is connected to)
#   .\set-secrets.ps1 -TokenOnly         only refresh the 3 Gmail values, keep the current passphrase
#   .\set-secrets.ps1 -Repo owner/name   name the repo yourself
param(
    [string]$Repo,
    [switch]$TokenOnly
)

$repo = if ($Repo) { $Repo } else { gh repo view --json nameWithOwner --jq .nameWithOwner }
if (-not $repo) { Write-Host "Could not work out the GitHub repo. Pass it as: .\set-secrets.ps1 -Repo owner/name" -ForegroundColor Red; exit 1 }
Write-Host "Setting secrets on $repo"
$file = Join-Path $PSScriptRoot "github-secrets.txt"
if (-not (Test-Path $file)) { Write-Host "github-secrets.txt not found in this folder. Run get_token.py first." -ForegroundColor Red; exit 1 }

foreach ($line in Get-Content $file) {
    if (-not $line.Contains("=")) { continue }
    $name, $value = $line -split "=", 2
    $value | gh secret set $name --repo $repo
    if ($LASTEXITCODE -ne 0) { Write-Host "Failed to set $name" -ForegroundColor Red; exit 1 }
}

if (-not $TokenOnly) {
    function Read-Plain($prompt) {
        $s = Read-Host $prompt -AsSecureString
        $b = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($s)
        try { [Runtime.InteropServices.Marshal]::PtrToStringBSTR($b) } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($b) }
    }

    while ($true) {
        $p1 = Read-Plain "Choose your dashboard passphrase (long, e.g. 4-5 random words; at least 12 characters)"
        $p2 = Read-Plain "Type it again"
        if ($p1 -ne $p2) { Write-Host "They do not match, try again." -ForegroundColor Yellow; continue }
        if ($p1.Length -lt 12) { Write-Host "Too short. Use at least 12 characters." -ForegroundColor Yellow; continue }
        break
    }
    $p1 | gh secret set DASHBOARD_PASSPHRASE --repo $repo
    if ($LASTEXITCODE -ne 0) { Write-Host "Failed to set DASHBOARD_PASSPHRASE" -ForegroundColor Red; exit 1 }
    Write-Host "`nAll 4 secrets are saved in GitHub. Remember your passphrase; it cannot be recovered, only replaced." -ForegroundColor Green
} else {
    Write-Host "`nThe 3 Gmail secrets were refreshed. Your passphrase was not changed." -ForegroundColor Green
}

$del = Read-Host "Delete github-secrets.txt from this PC now? (y/n)"
if ($del -eq "y") { Remove-Item $file; Write-Host "Deleted." }
