param(
    [string]$InputFile = 'leads_testing.csv',
    [string]$OutputFile = 'outreach_testing.json',
    [string]$AsOf = '2024-01-20',
    [ValidateSet('ollama', 'openai')]
    [string]$Provider = 'ollama',
    [string]$Model = '',
    [ValidateRange(2, 20)]
    [int]$BatchSize = 2,
    [ValidateRange(1, 1800)]
    [int]$RequestTimeout = 180
)

# Run the installed local model by default; only an explicit OpenAI selection needs a key.
# No key is read, prompted for, or sent by the default Ollama path.
$previousApiKey = $null
if ($Provider -eq 'openai') { $previousApiKey = $env:OPENAI_API_KEY }
$secureApiKey = $null
$outreachExitCode = 1
try {
    if ($Provider -eq 'openai' -and [string]::IsNullOrWhiteSpace($env:OPENAI_API_KEY)) {
        $secureApiKey = Read-Host 'Paste your OpenAI API key (input is hidden)' -AsSecureString
        $env:OPENAI_API_KEY = [System.Net.NetworkCredential]::new('', $secureApiKey).Password
    }
    $projectPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $projectPython)) {
        throw 'Project Python is missing. Create it with: python -m venv .venv'
    }
    $inputPath = if ([System.IO.Path]::IsPathRooted($InputFile)) { $InputFile } else { Join-Path $PSScriptRoot $InputFile }
    $outputPath = if ([System.IO.Path]::IsPathRooted($OutputFile)) { $OutputFile } else { Join-Path $PSScriptRoot $OutputFile }
    $draftArguments = @((Join-Path $PSScriptRoot 'main.py'), $inputPath,
        '--as-of', $AsOf, '--output', $outputPath, '--draft-outreach',
        '--provider', $Provider, '--batch-size', $BatchSize,
        '--request-timeout', $RequestTimeout)
    if (-not [string]::IsNullOrWhiteSpace($Model)) { $draftArguments += @('--model', $Model) }
    & $projectPython @draftArguments
    $outreachExitCode = $LASTEXITCODE
}
finally {
    if ($Provider -eq 'openai') { $env:OPENAI_API_KEY = $previousApiKey }
    if ($null -ne $secureApiKey) { $secureApiKey.Dispose() }
}
exit $outreachExitCode
