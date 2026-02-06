# Hook: skill-router.ps1
# Type: UserPromptSubmit
# Purpose: Detects project context and outputs DIRECTIVE to load relevant skills
# Skills provide domain-specific patterns that reduce implementation errors

$ErrorActionPreference = "SilentlyContinue"

# Read JSON input from Claude Code via stdin
$rawInput = [Console]::In.ReadToEnd()
$UserPrompt = ""

try {
    $parsed = $rawInput | ConvertFrom-Json
    if ($parsed.prompt) {
        $UserPrompt = $parsed.prompt
    } elseif ($parsed.message -and $parsed.message.content) {
        $UserPrompt = $parsed.message.content
    } elseif ($parsed.content) {
        $UserPrompt = $parsed.content
    } else {
        $UserPrompt = $rawInput
    }
} catch {
    $UserPrompt = $rawInput
}

$UserPrompt = $UserPrompt.ToLower()

# ═══════════════════════════════════════════════════════════════════════════════
# FILE CONTEXT DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

$CurrentDir = Get-Location
$MatchedSkills = @()

# Python Detection
$PythonFiles = Get-ChildItem -Path $CurrentDir -Recurse -Depth 3 -Include "*.py", "requirements.txt", "pyproject.toml", "setup.py" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($PythonFiles -or $UserPrompt -match "python|django|flask|fastapi|pytest") {
    $MatchedSkills += @{
        name = "python-development"
        reason = if ($PythonFiles) { "Python files detected" } else { "Python mentioned in prompt" }
    }
}

# TypeScript/JavaScript Detection
$TSFiles = Get-ChildItem -Path $CurrentDir -Recurse -Depth 3 -Include "*.ts", "*.tsx", "*.js", "*.jsx", "package.json", "tsconfig.json" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($TSFiles -or $UserPrompt -match "typescript|javascript|react|vue|angular|node|next") {
    $MatchedSkills += @{
        name = "typescript-development"
        reason = if ($TSFiles) { "TypeScript/JS files detected" } else { "TypeScript/JS mentioned in prompt" }
    }
}

# Terraform Detection
$TFFiles = Get-ChildItem -Path $CurrentDir -Recurse -Depth 3 -Include "*.tf", "*.tfvars" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($TFFiles -or $UserPrompt -match "terraform|\.tf|infrastructure") {
    $MatchedSkills += @{
        name = "terraform-infrastructure"
        reason = if ($TFFiles) { "Terraform files detected" } else { "Terraform mentioned in prompt" }
    }
}

# Testing Detection (supplement skill)
$TestFiles = Get-ChildItem -Path $CurrentDir -Recurse -Depth 3 -Include "*test*.py", "*test*.ts", "*test*.js", "*spec*.ts", "*spec*.js" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($TestFiles -or $UserPrompt -match "test|testing|coverage|jest|pytest|vitest") {
    $MatchedSkills += @{
        name = "testing-best-practices"
        reason = if ($TestFiles) { "Test files detected" } else { "Testing mentioned in prompt" }
    }
}

# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUT: DIRECTIVE FORMAT
# ═══════════════════════════════════════════════════════════════════════════════

if ($MatchedSkills.Count -gt 0) {
    # Limit to 2 most relevant skills to control token usage
    $TopSkills = $MatchedSkills | Select-Object -First 2
    
    Write-Output ""
    Write-Output "╔═══════════════════════════════════════════════════════════════╗"
    
    foreach ($skill in $TopSkills) {
        Write-Output "║ 📚 LOAD:$($skill.name)"
        Write-Output "║    → Read .claude/skills/$($skill.name)/SKILL.md FIRST"
        Write-Output "║    Reason: $($skill.reason)"
    }
    
    Write-Output "║                                                               "
    Write-Output "║ DIRECTIVE: Load skill instructions BEFORE implementation      "
    Write-Output "╚═══════════════════════════════════════════════════════════════╝"
    Write-Output ""
}

exit 0
