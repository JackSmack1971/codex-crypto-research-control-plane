param(
  [Parameter(Mandatory=$true, Position=0)]
  [string]$Script,

  [Parameter(ValueFromRemainingArguments=$true)]
  [string[]]$ScriptArgs
)

$ErrorActionPreference = 'Stop'
$env:PYTHONDONTWRITEBYTECODE = '1'

$candidates = @(
  @{ Command = 'py'; Prefix = @('-3') },
  @{ Command = 'python'; Prefix = @() },
  @{ Command = 'python3'; Prefix = @() }
)

foreach ($candidate in $candidates) {
  $resolved = Get-Command $candidate.Command -ErrorAction SilentlyContinue
  if (-not $resolved) { continue }

  & $candidate.Command @($candidate.Prefix) -B -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 2)" *> $null
  if ($LASTEXITCODE -ne 0) { continue }

  & $candidate.Command @($candidate.Prefix) -B $Script @ScriptArgs
  exit $LASTEXITCODE
}

Write-Error 'No working Python 3.11+ interpreter was found through py -3, python, or python3.'
exit 127
