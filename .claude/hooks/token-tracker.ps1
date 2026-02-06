# Hook: token-tracker.ps1
# Type: PostToolUse
# Purpose: Tracks tool usage patterns for token optimization analysis
# Lightweight - minimal output to avoid adding tokens

$ErrorActionPreference = "SilentlyContinue"

# Read JSON input from Claude Code via stdin
$rawInput = ""
try { $rawInput = [Console]::In.ReadToEnd() } catch {}

$ToolName = ""
$ToolDuration = ""
try {
    $parsed = $rawInput | ConvertFrom-Json
    if ($parsed.tool_name) { $ToolName = $parsed.tool_name }
    elseif ($parsed.tool) { $ToolName = $parsed.tool }
    if ($parsed.duration) { $ToolDuration = $parsed.duration }
    elseif ($parsed.tool_duration) { $ToolDuration = $parsed.tool_duration }
} catch {}

# Fallback to environment variables
if (-not $ToolName -and $env:TOOL_NAME) { $ToolName = $env:TOOL_NAME }
if (-not $ToolDuration -and $env:TOOL_DURATION) { $ToolDuration = $env:TOOL_DURATION }

$LogDir = ".claude\logs"
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

# Append to daily log
$Date = Get-Date -Format "yyyy-MM-dd"
$Time = Get-Date -Format "HH:mm:ss"
$LogFile = "$LogDir\tokens-$Date.log"

$Entry = "$Time|$ToolName|$ToolDuration"
Add-Content -Path $LogFile -Value $Entry

# Track session statistics (in-memory via file)
$StatsFile = "$LogDir\.session-stats"
$ToolCount = 0

if (Test-Path $StatsFile) {
    $ToolCount = [int](Get-Content $StatsFile -ErrorAction SilentlyContinue)
}
$ToolCount++
Set-Content -Path $StatsFile -Value $ToolCount

# Alert if tool count is getting high (token concern)
if ($ToolCount -eq 50) {
    Write-Output ""
    Write-Output "⚡ SESSION STATS: 50 tool calls executed"
    Write-Output "   Consider: Are we approaching token limits?"
    Write-Output "   Recommendation: Verify progress against goals"
    Write-Output ""
}

if ($ToolCount -eq 100) {
    Write-Output ""
    Write-Output "⚠️ SESSION STATS: 100 tool calls executed"
    Write-Output "   HIGH TOKEN USAGE - Evaluate if task should be phased"
    Write-Output ""
}

exit 0
