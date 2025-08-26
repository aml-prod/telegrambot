param(
  [int]$Port = 8080,
  [ValidateSet('cloudflared','ngrok')]
  [string]$Tunnel = 'cloudflared'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPy = Join-Path $root '.venv\Scripts\python.exe'
if (!(Test-Path $venvPy)) { throw "Missing $venvPy. Create venv and install requirements." }

function Test-Cmd { param([string]$Name) (Get-Command $Name -ErrorAction SilentlyContinue) -ne $null }
function Set-PublicBaseUrl {
  param([string]$File, [string]$Url)
  $lines = @()
  if (Test-Path $File) { $lines = Get-Content $File }
  $found = $false
  $out = foreach ($l in $lines) {
    if ($l -match '^PUBLIC_BASE_URL=') { $found = $true; "PUBLIC_BASE_URL=$Url" } else { $l }
  }
  if (-not $found) { $out += "PUBLIC_BASE_URL=$Url" }
  $out | Set-Content -Encoding ascii $File
}

# 1) link_server
Write-Host "[1/4] Start link_server on http://127.0.0.1:$Port"
$ls = Start-Process -FilePath $venvPy -ArgumentList @('-m','bot.link_server') -WorkingDirectory $root -PassThru -WindowStyle Hidden

# 2) Tunnel
$logOut = Join-Path $root "tunnel.out.log"
$logErr = Join-Path $root "tunnel.err.log"
if (Test-Path $logOut) { Remove-Item $logOut -Force }
if (Test-Path $logErr) { Remove-Item $logErr -Force }

if ($Tunnel -eq 'cloudflared') {
  if (!(Test-Cmd 'cloudflared')) { throw "cloudflared not found. Install: winget install Cloudflare.cloudflared" }
  $args = "tunnel --url http://127.0.0.1:$Port"
  $tn = Start-Process -FilePath 'cloudflared' -ArgumentList $args -RedirectStandardOutput $logOut -RedirectStandardError $logErr -PassThru
} else {
  if (!(Test-Cmd 'ngrok')) { throw "ngrok not found. Install: winget install ngrok.ngrok" }
  $args = "http $Port"
  $tn = Start-Process -FilePath 'ngrok' -ArgumentList $args -RedirectStandardOutput $logOut -RedirectStandardError $logErr -PassThru
}

# 3) Wait for public URL
Write-Host "[2/4] Waiting for public URL..."
$publicUrl = $null
for ($i=0; $i -lt 120 -and -not $publicUrl; $i++) {
  Start-Sleep -Milliseconds 500
  $textOut = (Get-Content $logOut -Raw -ErrorAction SilentlyContinue)
  $textErr = (Get-Content $logErr -Raw -ErrorAction SilentlyContinue)
  $text = "$textOut`n$textErr"

  if ($Tunnel -eq 'cloudflared') {
    if ($text -match 'https://[a-z0-9\-\.]+\.trycloudflare\.com') { $publicUrl = $Matches[0] }
  } else {
    if ($text -match 'https://[a-z0-9\-]+\.ngrok\.io') { $publicUrl = $Matches[0] }
    if (-not $publicUrl -and $text -match 'url=(https://[^ \r\n]+)') { $publicUrl = $Matches[1] }
  }
}
if (-not $publicUrl) { Write-Warning "Public URL not found in logs: $logOut, $logErr"; exit 1 }

# 4) Update .env
Write-Host "[3/4] PUBLIC_BASE_URL = $publicUrl"
$envFile = Join-Path $root ".env"
Set-PublicBaseUrl -File $envFile -Url $publicUrl

# 5) Start bot
Write-Host "[4/4] Start bot (polling)"
$bot = Start-Process -FilePath $venvPy -ArgumentList @('-m','bot') -WorkingDirectory $root -PassThru

Write-Host ""
Write-Host "Done."
Write-Host ("link_server PID: {0}" -f $ls.Id)
Write-Host ("tunnel     PID: {0}" -f $tn.Id)
Write-Host ("bot        PID: {0}" -f $bot.Id)
Write-Host ("Public URL : {0}" -f $publicUrl)
Write-Host ("Tunnel log : {0}" -f $logOut)
Write-Host ("Tunnel err : {0}" -f $logErr)