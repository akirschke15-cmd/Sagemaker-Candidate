# Hook: conformance-gate.ps1
# Type: PostToolUse
# Purpose: Validates implementation quality, flags violations, reminds about standards
# Runs after EVERY tool use to maintain implementation quality

$ErrorActionPreference = "SilentlyContinue"

# Read JSON input from Claude Code via stdin
$rawInput = ""
try { $rawInput = [Console]::In.ReadToEnd() } catch {}

$ToolName = "unknown"
try {
    $parsed = $rawInput | ConvertFrom-Json
    if ($parsed.tool_name) {
        $ToolName = $parsed.tool_name
    } elseif ($parsed.tool) {
        $ToolName = $parsed.tool
    }
} catch {}

# Fallback to environment variable
if ($ToolName -eq "unknown" -and $env:TOOL_NAME) {
    $ToolName = $env:TOOL_NAME
}

# ═══════════════════════════════════════════════════════════════════════════════
# LOGGING SETUP
# ═══════════════════════════════════════════════════════════════════════════════

$LogDir = ".claude\logs"
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

$Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path "$LogDir\tool-usage.log" -Value "[$Timestamp] $ToolName"

# ═══════════════════════════════════════════════════════════════════════════════
# VIOLATION DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

$Violations = @()
$Warnings = @()

# Check for file write operations
if ($ToolName -match "Write|Edit|Create") {
    
    # Scan recently modified files for anti-patterns
    $RecentFiles = Get-ChildItem -Path . -Recurse -Depth 4 -File -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -gt (Get-Date).AddMinutes(-5) } |
        Where-Object { $_.Extension -match "\.(ts|tsx|js|jsx|py)$" }
    
    foreach ($file in $RecentFiles) {
        $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
        
        if ($content) {
            # VIOLATION: Mock data in production code
            if ($content -match "const mock|mockData|MOCK_|fakeDat|stubDat" -and $file.Name -notmatch "test|spec|mock") {
                $Violations += "MOCK_DATA: $($file.Name) contains mock data without test context"
            }
            
            # VIOLATION: TODO in core functionality
            if ($content -match "TODO:.*implement|FIXME:.*later|TODO:.*connect") {
                $Warnings += "TODO_FOUND: $($file.Name) has TODO for core functionality"
            }
            
            # VIOLATION: Hardcoded credentials (security)
            if ($content -match "password\s*=\s*['""]|apiKey\s*=\s*['""]|secret\s*=\s*['""]" -and $file.Name -notmatch "test|example") {
                $Violations += "HARDCODED_SECRET: $($file.Name) may contain hardcoded credentials"
            }
            
            # WARNING: Console.log in production
            if ($content -match "console\.log" -and $file.Name -notmatch "test|spec|debug") {
                $Warnings += "DEBUG_CODE: $($file.Name) contains console.log statements"
            }
        }
    }
}

# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUT: VIOLATIONS & REMINDERS
# ═══════════════════════════════════════════════════════════════════════════════

if ($Violations.Count -gt 0 -or $Warnings.Count -gt 0) {
    Write-Output ""
    
    if ($Violations.Count -gt 0) {
        Write-Output "╔═══════════════════════════════════════════════════════════════╗"
        Write-Output "║ 🚨 CONFORMANCE VIOLATIONS DETECTED                            "
        Write-Output "╠═══════════════════════════════════════════════════════════════╣"
        foreach ($v in $Violations) {
            Write-Output "║ ❌ $v"
        }
        Write-Output "╠═══════════════════════════════════════════════════════════════╣"
        Write-Output "║ ACTION REQUIRED: Fix violations before marking complete       "
        Write-Output "╚═══════════════════════════════════════════════════════════════╝"
    }
    
    if ($Warnings.Count -gt 0) {
        Write-Output "╔═══════════════════════════════════════════════════════════════╗"
        Write-Output "║ ⚠️ WARNINGS                                                   "
        Write-Output "╠═══════════════════════════════════════════════════════════════╣"
        foreach ($w in $Warnings) {
            Write-Output "║ ⚡ $w"
        }
        Write-Output "╚═══════════════════════════════════════════════════════════════╝"
    }
    
    Write-Output ""
}

# ═══════════════════════════════════════════════════════════════════════════════
# CONTEXTUAL REMINDERS (once per session)
# ═══════════════════════════════════════════════════════════════════════════════

$ReminderFile = ".claude\.session-reminders"

if ($ToolName -match "Write|Edit") {
    if (-not (Test-Path $ReminderFile)) {
        # First write of session - show full reminder
        Write-Output ""
        Write-Output "╔═══════════════════════════════════════════════════════════════╗"
        Write-Output "║ 📋 PRE-COMPLETION CHECKLIST (verify before marking done)      "
        Write-Output "╠═══════════════════════════════════════════════════════════════╣"
        Write-Output "║ □ All acceptance criteria from PRD pass                       "
        Write-Output "║ □ UI connects to real API (no mock data)                      "
        Write-Output "║ □ API connects to real database (no stubs)                    "
        Write-Output "║ □ Error handling works                                        "
        Write-Output "║ □ Loading states work                                         "
        Write-Output "║ □ TodoWrite is 100% complete                                  "
        Write-Output "╚═══════════════════════════════════════════════════════════════╝"
        Write-Output ""
        
        # Create reminder file to prevent spam
        New-Item -ItemType File -Path $ReminderFile -Force | Out-Null
    }
}

# Clean up reminder file if older than 2 hours (new session)
$existingReminder = Get-Item $ReminderFile -ErrorAction SilentlyContinue
if ($existingReminder -and $existingReminder.LastWriteTime -lt (Get-Date).AddHours(-2)) {
    Remove-Item $ReminderFile -Force -ErrorAction SilentlyContinue
}

exit 0
