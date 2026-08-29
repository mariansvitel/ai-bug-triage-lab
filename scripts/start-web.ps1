$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$candidateEnvFiles = @(
    (Join-Path $repoRoot ".env.local"),
    (Join-Path (Split-Path -Parent $repoRoot) ".env.local")
)

foreach ($candidate in $candidateEnvFiles) {
    if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
        continue
    }

    $keyLine = Get-Content -LiteralPath $candidate |
        Where-Object { $_ -match '^OPENAI_API_KEY=\S+' } |
        Select-Object -First 1

    if ($keyLine) {
        $env:OPENAI_API_KEY = $keyLine.Substring($keyLine.IndexOf('=') + 1)
        break
    }
}

if (-not $env:OPENAI_API_KEY) {
    throw "OPENAI_API_KEY was not found in the process environment or an ignored .env.local file."
}

$server = Join-Path $repoRoot ".venv\Scripts\ai-bug-triage-web.exe"
if (-not (Test-Path -LiteralPath $server -PathType Leaf)) {
    throw "The local environment is missing. Run: python -m venv .venv; .\.venv\Scripts\python.exe -m pip install -e '.[dev]'"
}

Set-Location -LiteralPath $repoRoot
& $server
