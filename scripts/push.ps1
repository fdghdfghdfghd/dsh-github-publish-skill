param(
    [string]$Path = ".",
    [string]$Branch = "main",
    [string]$Message = "update",
    [string]$Remote = "",
    [string]$KeyDir = (Join-Path $HOME ".dsh-github"),
    [switch]$Init,
    [switch]$Commit,
    [switch]$DryRun
)

# git writes progress to stderr; keep Continue and check $LASTEXITCODE instead.
$ErrorActionPreference = "Continue"

$Key = Join-Path $KeyDir "id_ed25519"
$KnownHosts = Join-Path $KeyDir "known_hosts"
$Wrapper = Join-Path $KeyDir "ssh_wrap.cmd"

if (-not (Test-Path $Key)) {
    throw "No SSH key at $Key. Run scripts/setup_ssh.ps1 first."
}

New-Item -ItemType Directory -Force -Path $KeyDir | Out-Null
if (-not (Test-Path $KnownHosts)) { New-Item -ItemType File -Force -Path $KnownHosts | Out-Null }

# git on Windows routes GIT_SSH_COMMAND through sh, which breaks in restricted
# environments. A .cmd wrapper is exec'd directly instead.
$wrapBody = @"
@echo off
ssh.exe -i "$Key" -o IdentitiesOnly=yes -o UserKnownHostsFile="$KnownHosts" -o StrictHostKeyChecking=accept-new %*
"@
$wrapBody | Out-File -FilePath $Wrapper -Encoding ascii

$env:GIT_SSH = $Wrapper
$env:GIT_SSH_VARIANT = "ssh"

$repo = (Resolve-Path $Path).Path
Write-Host "repo : $repo"
Write-Host "key  : $Key"

Push-Location $repo
try {
    $inside = git rev-parse --is-inside-work-tree 2>$null
    if ($inside -ne "true") {
        if ($Init) {
            git init | Out-Null
            Write-Host "initialized empty repository"
        } else {
            throw "Not a git repository. Re-run with -Init."
        }
    }

    if ($Commit) {
        git add -A
        git -c user.name="$env:USERNAME" -c user.email="$env:USERNAME@users.noreply.github.com" commit -m "$Message"
        if ($LASTEXITCODE -ne 0) { Write-Host "nothing to commit" }
    }

    if ($Remote -ne "") {
        $existing = git remote 2>$null
        if ($existing -contains "origin") { git remote set-url origin $Remote } else { git remote add origin $Remote }
        Write-Host "remote set: $Remote"
    }

    $pushArgs = @("push", "-u", "origin", $Branch)
    if ($DryRun) { $pushArgs = @("push", "--dry-run", "-u", "origin", $Branch) }

    git @pushArgs
    if ($LASTEXITCODE -ne 0) { throw "git push failed (exit $LASTEXITCODE)" }

    Write-Host ""
    Write-Host "remote refs:"
    git ls-remote origin 2>$null
} finally {
    Pop-Location
}
