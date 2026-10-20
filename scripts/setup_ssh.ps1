param(
    [string]$KeyDir = (Join-Path $HOME ".dsh-github"),
    [switch]$Regenerate
)

$ErrorActionPreference = "Stop"

$Key = Join-Path $KeyDir "id_ed25519"
$KnownHosts = Join-Path $KeyDir "known_hosts"
$Wrapper = Join-Path $KeyDir "ssh_wrap.cmd"

New-Item -ItemType Directory -Force -Path $KeyDir | Out-Null
if (-not (Test-Path $KnownHosts)) { New-Item -ItemType File -Force -Path $KnownHosts | Out-Null }

if ($Regenerate -or -not (Test-Path $Key)) {
    if (Test-Path $Key) { Remove-Item $Key -Force }
    # empty passphrase; ssh-keygen takes "" as an empty argument string
    cmd /c "ssh-keygen -t ed25519 -f `"$Key`" -N `"`" -C dsh-github -q"
    Write-Host "generated new key: $Key"
}

$pubText = (& ssh-keygen -y -f $Key) 2>$null
if (-not $pubText) { throw "could not derive public key from $Key" }

$wrapBody = @"
@echo off
ssh.exe -i "$Key" -o IdentitiesOnly=yes -o UserKnownHostsFile="$KnownHosts" -o StrictHostKeyChecking=accept-new %*
"@
$wrapBody | Out-File -FilePath $Wrapper -Encoding ascii

Write-Host ""
Write-Host "Public key — add it at https://github.com/settings/ssh/new :"
Write-Host ""
Write-Host ("  " + $pubText)
Write-Host ""

Write-Host "Testing authentication..."
& ssh -i $Key -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=15 `
      -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=$KnownHosts `
      -T git@github.com 2>&1 | ForEach-Object { Write-Host "  $_" }

Write-Host ""
Write-Host "Note: ssh -T exits with 1 even on success (GitHub provides no shell)."
Write-Host "A 'Hi <user>!' line above means the key works."
