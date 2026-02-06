# Hook: agent-router.ps1
# Type: UserPromptSubmit  
# Purpose: Outputs DIRECTIVE for Claude to invoke specific agent via Task tool
# CRITICAL: Output format triggers Claude's mandatory agent invocation

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

# Agent scoring system - highest score wins
$AgentScores = @{}

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1: REQUIREMENTS (Score: 100+ for critical triggers)
# ═══════════════════════════════════════════════════════════════════════════════

# Product Manager - Requirements definition
$PM_Triggers = @(
    @{ pattern = "requirements"; score = 100 },
    @{ pattern = "user stor"; score = 100 },
    @{ pattern = "prd"; score = 100 },
    @{ pattern = "product spec"; score = 100 },
    @{ pattern = "acceptance criteria"; score = 95 },
    @{ pattern = "what should we build"; score = 90 },
    @{ pattern = "define feature"; score = 85 },
    @{ pattern = "feature request"; score = 80 }
)
$PM_AntiPatterns = @("implement", "code", "debug", "fix", "deploy")

$score = 0
foreach ($trigger in $PM_Triggers) {
    if ($UserPrompt -match $trigger.pattern) { $score += $trigger.score }
}
foreach ($anti in $PM_AntiPatterns) {
    if ($UserPrompt -match $anti) { $score -= 50 }
}
if ($score -gt 0) { $AgentScores["product-manager"] = $score }

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2: DESIGN (Score: 100+ for critical triggers)
# ═══════════════════════════════════════════════════════════════════════════════

# System Architect
$ARCH_Triggers = @(
    @{ pattern = "architect"; score = 100 },
    @{ pattern = "system design"; score = 100 },
    @{ pattern = "design.*system"; score = 95 },
    @{ pattern = "how.*structure"; score = 90 },
    @{ pattern = "scalab"; score = 85 },
    @{ pattern = "microservice"; score = 85 },
    @{ pattern = "design pattern"; score = 80 }
)
$score = 0
foreach ($trigger in $ARCH_Triggers) {
    if ($UserPrompt -match $trigger.pattern) { $score += $trigger.score }
}
if ($score -gt 0) { $AgentScores["system-architect"] = $score }

# API Designer
$API_Triggers = @(
    @{ pattern = "design.*api"; score = 100 },
    @{ pattern = "api.*design"; score = 100 },
    @{ pattern = "rest.*api"; score = 90 },
    @{ pattern = "graphql.*schema"; score = 90 },
    @{ pattern = "openapi"; score = 85 },
    @{ pattern = "swagger"; score = 80 },
    @{ pattern = "endpoint.*design"; score = 80 }
)
$score = 0
foreach ($trigger in $API_Triggers) {
    if ($UserPrompt -match $trigger.pattern) { $score += $trigger.score }
}
if ($score -gt 0) { $AgentScores["api-designer"] = $score }

# UI Designer
$UI_Triggers = @(
    @{ pattern = "ui.*design"; score = 100 },
    @{ pattern = "ux.*design"; score = 100 },
    @{ pattern = "design.*system"; score = 95 },
    @{ pattern = "wireframe"; score = 95 },
    @{ pattern = "mockup"; score = 90 },
    @{ pattern = "prototype"; score = 90 },
    @{ pattern = "design.*token"; score = 85 },
    @{ pattern = "design.*spec"; score = 85 },
    @{ pattern = "layout.*design"; score = 80 },
    @{ pattern = "design.*handoff"; score = 80 }
)
$UI_AntiPatterns = @("implement.*ui", "code.*ui", "build.*ui")
$score = 0
foreach ($trigger in $UI_Triggers) {
    if ($UserPrompt -match $trigger.pattern) { $score += $trigger.score }
}
foreach ($anti in $UI_AntiPatterns) {
    if ($UserPrompt -match $anti) { $score -= 50 }
}
if ($score -gt 0) { $AgentScores["ui-designer"] = $score }

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 3: IMPLEMENTATION (Score: 100+ for critical triggers)
# ═══════════════════════════════════════════════════════════════════════════════

# Frontend Engineer
$FE_Triggers = @(
    @{ pattern = "build.*ui"; score = 100 },
    @{ pattern = "build.*component"; score = 100 },
    @{ pattern = "create.*component"; score = 95 },
    @{ pattern = "frontend"; score = 90 },
    @{ pattern = "react"; score = 85 },
    @{ pattern = "vue"; score = 85 },
    @{ pattern = "tailwind"; score = 80 },
    @{ pattern = "css"; score = 75 },
    @{ pattern = "responsive"; score = 70 }
)
$score = 0
foreach ($trigger in $FE_Triggers) {
    if ($UserPrompt -match $trigger.pattern) { $score += $trigger.score }
}
if ($score -gt 0) { $AgentScores["frontend-engineer"] = $score }

# Backend Engineer  
$BE_Triggers = @(
    @{ pattern = "build.*api"; score = 100 },
    @{ pattern = "create.*endpoint"; score = 100 },
    @{ pattern = "backend"; score = 95 },
    @{ pattern = "database"; score = 90 },
    @{ pattern = "server"; score = 85 },
    @{ pattern = "authentication"; score = 85 },
    @{ pattern = "api.*implement"; score = 85 }
)
$score = 0
foreach ($trigger in $BE_Triggers) {
    if ($UserPrompt -match $trigger.pattern) { $score += $trigger.score }
}
if ($score -gt 0) { $AgentScores["backend-engineer"] = $score }

# Fullstack Engineer - triggers on end-to-end scope
$FS_Triggers = @(
    @{ pattern = "fullstack"; score = 100 },
    @{ pattern = "full-stack"; score = 100 },
    @{ pattern = "full stack"; score = 100 },
    @{ pattern = "end.to.end"; score = 95 },
    @{ pattern = "frontend.*backend"; score = 90 },
    @{ pattern = "complete.*feature"; score = 85 }
)
$score = 0
foreach ($trigger in $FS_Triggers) {
    if ($UserPrompt -match $trigger.pattern) { $score += $trigger.score }
}
if ($score -gt 0) { $AgentScores["fullstack-engineer"] = $score }

# ═══════════════════════════════════════════════════════════════════════════════
# LANGUAGE SPECIALISTS (Score: 80+ for explicit mentions)
# ═══════════════════════════════════════════════════════════════════════════════

# Python Expert
if ($UserPrompt -match "python|django|flask|fastapi|pytest|\.py") {
    $AgentScores["python-expert"] = [Math]::Max($AgentScores["python-expert"], 80)
}

# TypeScript Expert
if ($UserPrompt -match "typescript|react|next\.?js|\.tsx?|node") {
    $AgentScores["typescript-expert"] = [Math]::Max($AgentScores["typescript-expert"], 80)
}

# Terraform Expert
if ($UserPrompt -match "terraform|\.tf|tfvars|infrastructure.as.code") {
    $AgentScores["terraform-expert"] = [Math]::Max($AgentScores["terraform-expert"], 80)
}

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 4: TESTING (Score: 100+ for critical triggers)
# ═══════════════════════════════════════════════════════════════════════════════

# Test Architect (strategy)
$TA_Triggers = @(
    @{ pattern = "test.*strategy"; score = 100 },
    @{ pattern = "testing.*strategy"; score = 100 },
    @{ pattern = "test.*architecture"; score = 95 },
    @{ pattern = "how.*should.*test"; score = 90 },
    @{ pattern = "testing.*approach"; score = 85 }
)
$TA_AntiPatterns = @("run.*test", "execute.*test", "write.*test.*for")
$score = 0
foreach ($trigger in $TA_Triggers) {
    if ($UserPrompt -match $trigger.pattern) { $score += $trigger.score }
}
foreach ($anti in $TA_AntiPatterns) {
    if ($UserPrompt -match $anti) { $score -= 60 }
}
if ($score -gt 0) { $AgentScores["test-architect"] = $score }

# QA Engineer (execution)
$QA_Triggers = @(
    @{ pattern = "write.*test"; score = 100 },
    @{ pattern = "create.*test"; score = 100 },
    @{ pattern = "test.*this"; score = 95 },
    @{ pattern = "run.*test"; score = 90 },
    @{ pattern = "coverage"; score = 85 },
    @{ pattern = "validate"; score = 80 }
)
$QA_AntiPatterns = @("test.*strategy", "testing.*approach")
$score = 0
foreach ($trigger in $QA_Triggers) {
    if ($UserPrompt -match $trigger.pattern) { $score += $trigger.score }
}
foreach ($anti in $QA_AntiPatterns) {
    if ($UserPrompt -match $anti) { $score -= 60 }
}
if ($score -gt 0) { $AgentScores["qa-engineer"] = $score }

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 5: REVIEW & QUALITY (Score: 100+ for critical triggers)
# ═══════════════════════════════════════════════════════════════════════════════

# Code Reviewer
$CR_Triggers = @(
    @{ pattern = "review.*code"; score = 100 },
    @{ pattern = "code.*review"; score = 100 },
    @{ pattern = "review.*pr"; score = 95 },
    @{ pattern = "pull.*request"; score = 90 },
    @{ pattern = "check.*quality"; score = 85 }
)
$score = 0
foreach ($trigger in $CR_Triggers) {
    if ($UserPrompt -match $trigger.pattern) { $score += $trigger.score }
}
if ($score -gt 0) { $AgentScores["code-reviewer"] = $score }

# Security Auditor
$SEC_Triggers = @(
    @{ pattern = "security.*review"; score = 100 },
    @{ pattern = "security.*audit"; score = 100 },
    @{ pattern = "vulnerabilit"; score = 95 },
    @{ pattern = "owasp"; score = 90 },
    @{ pattern = "penetration"; score = 90 },
    @{ pattern = "xss|sql.*injection"; score = 85 }
)
$score = 0
foreach ($trigger in $SEC_Triggers) {
    if ($UserPrompt -match $trigger.pattern) { $score += $trigger.score }
}
if ($score -gt 0) { $AgentScores["security-auditor"] = $score }

# ═══════════════════════════════════════════════════════════════════════════════
# TROUBLESHOOTING (Score: 100+ for critical triggers)
# ═══════════════════════════════════════════════════════════════════════════════

# Debugger
$DBG_Triggers = @(
    @{ pattern = "debug"; score = 100 },
    @{ pattern = "fix.*bug"; score = 100 },
    @{ pattern = "not.*working"; score = 95 },
    @{ pattern = "error"; score = 90 },
    @{ pattern = "broken"; score = 90 },
    @{ pattern = "issue"; score = 80 }
)
$score = 0
foreach ($trigger in $DBG_Triggers) {
    if ($UserPrompt -match $trigger.pattern) { $score += $trigger.score }
}
if ($score -gt 0) { $AgentScores["debugger"] = $score }

# Performance Optimizer
$PERF_Triggers = @(
    @{ pattern = "performance"; score = 100 },
    @{ pattern = "optimi[zs]e"; score = 95 },
    @{ pattern = "slow"; score = 90 },
    @{ pattern = "bottleneck"; score = 90 },
    @{ pattern = "profil"; score = 85 },
    @{ pattern = "speed.*up"; score = 85 }
)
$score = 0
foreach ($trigger in $PERF_Triggers) {
    if ($UserPrompt -match $trigger.pattern) { $score += $trigger.score }
}
if ($score -gt 0) { $AgentScores["performance-optimizer"] = $score }

# ═══════════════════════════════════════════════════════════════════════════════
# INFRASTRUCTURE & DOCS
# ═══════════════════════════════════════════════════════════════════════════════

# DevOps Engineer
if ($UserPrompt -match "ci/cd|deploy|docker|kubernetes|pipeline|devops") {
    $AgentScores["devops-engineer"] = [Math]::Max($AgentScores["devops-engineer"], 90)
}

# Technical Writer
if ($UserPrompt -match "document|readme|docs|explain|write.*guide") {
    $AgentScores["technical-writer"] = [Math]::Max($AgentScores["technical-writer"], 85)
}

# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUT: DIRECTIVE FORMAT (not suggestion)
# ═══════════════════════════════════════════════════════════════════════════════

$ConfidenceThreshold = 70

# Get top agent
$TopAgent = $null
$TopScore = 0
foreach ($agent in $AgentScores.Keys) {
    if ($AgentScores[$agent] -gt $TopScore) {
        $TopScore = $AgentScores[$agent]
        $TopAgent = $agent
    }
}

# Output directive - fallback to fullstack-engineer if no agent meets threshold
if (-not $TopAgent -or $TopScore -lt $ConfidenceThreshold) {
    $TopAgent = "fullstack-engineer"
    $TopScore = "fallback"
}

Write-Output ""
Write-Output "╔═══════════════════════════════════════════════════════════════╗"
Write-Output "║ 🎯 INVOKE:$TopAgent (confidence:$TopScore)                    "
Write-Output "║                                                               "
Write-Output "║ DIRECTIVE: Use Task(subagent_type=""$TopAgent"")              "
Write-Output "║ DO NOT substitute with Explore/Plan                           "
Write-Output "║ DO NOT work directly - launch the agent                       "
Write-Output "╚═══════════════════════════════════════════════════════════════╝"
Write-Output ""

exit 0
