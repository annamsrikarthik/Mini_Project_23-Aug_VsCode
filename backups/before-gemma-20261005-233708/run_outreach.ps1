param(
    [string]$InputFile = 'leads_testing.csv',
    [string]$OutputFile = 'outreach_testing.json',
    [string]$AsOf = '2024-01-20',
    [string]$Model = 'gpt-4.1-mini'
)

# Ask for a key privately if it is not already set, then run the Python program.
# The key is never written to a file or printed; restore the prior environment on exit.
$previousApiKey = $env:OPENAI_API_KEY
$secureApiKey = $null
$outreachExitCode = 1
try {
    if ([string]::IsNullOrWhiteSpace($env:OPENAI_API_KEY)) {
        $secureApiKey = Read-Host 'Paste your OpenAI API key (input is hidden)' -AsSecureString
        $env:OPENAI_API_KEY = [System.Net.NetworkCredential]::new('', $secureApiKey).Password
    }
    $projectPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $projectPython)) {
        throw 'Project Python is missing. Create .venv and install requirements.txt first.'
    }
    $inputPath = if ([System.IO.Path]::IsPathRooted($InputFile)) { $InputFile } else { Join-Path $PSScriptRoot $InputFile }
    $outputPath = if ([System.IO.Path]::IsPathRooted($OutputFile)) { $OutputFile } else { Join-Path $PSScriptRoot $OutputFile }
    & $projectPython (Join-Path $PSScriptRoot 'main.py') $inputPath --as-of $AsOf --output $outputPath --draft-outreach --model $Model
    $outreachExitCode = $LASTEXITCODE
}
finally {
    $env:OPENAI_API_KEY = $previousApiKey
    if ($null -ne $secureApiKey) { $secureApiKey.Dispose() }
}
exit $outreachExitCode
