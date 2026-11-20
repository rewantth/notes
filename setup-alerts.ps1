# Turns on phone alerts. Run it yourself in PowerShell, inside this folder:
#     powershell -ExecutionPolicy Bypass -File .\setup-alerts.ps1
#
# What it does:
#   1. Makes a long random topic name (the private "channel" your phone listens to).
#   2. Saves it in GitHub as the secret NTFY_TOPIC.
#   3. Shows it on your screen and copies it to your clipboard so you can subscribe in the ntfy app.
#   4. Optionally sends a test alert.
#
# Needs the GitHub command-line tool (gh), signed in. Optional: pass -Repo owner/name.
param([string]$Repo)

$repo = if ($Repo) { $Repo } else { gh repo view --json nameWithOwner --jq .nameWithOwner }
if (-not $repo) { Write-Host "Could not work out the GitHub repo. Run: gh auth login   (or pass -Repo owner/name)" -ForegroundColor Red; exit 1 }

$bytes = New-Object byte[] 16
[Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
$topic = "jobhunt-" + (($bytes | ForEach-Object { $_.ToString("x2") }) -join "")

$topic | gh secret set NTFY_TOPIC --repo $repo
if ($LASTEXITCODE -ne 0) { Write-Host "Could not save the secret." -ForegroundColor Red; exit 1 }
try { Set-Clipboard -Value $topic } catch {}

Write-Host ""
Write-Host "Saved the secret NTFY_TOPIC on $repo." -ForegroundColor Green
Write-Host ""
Write-Host "Your private alert topic is:" -ForegroundColor Cyan
Write-Host "    $topic" -ForegroundColor Yellow
Write-Host "(It is also on your clipboard. Anyone who knows it could read your alerts, so keep it to yourself.)"
Write-Host ""
Write-Host "Now on your phone:"
Write-Host "  1. Install the free 'ntfy' app (Google Play, App Store, or F-Droid)."
Write-Host "  2. Tap the + button and choose 'Subscribe to topic'."
Write-Host "  3. Paste the topic above, keep the default server (ntfy.sh), and tap Subscribe."
Write-Host ""
$go = Read-Host "Subscribed? Send a test alert now? (y/n)"
if ($go -eq "y") {
    gh workflow run update.yml --repo $repo -f test_alert=true
    if ($LASTEXITCODE -eq 0) { Write-Host "Started. The alert should reach your phone in about two minutes." -ForegroundColor Green }
}
