# Framework 3.0 — Setup Guide

## What This Is

This framework makes Claude Code automatically invoke specialist AI agents and load domain-specific skills based on what you type. Instead of Claude guessing how to help, hooks analyze your prompt and issue **mandatory directives** that Claude must follow.

**Example**: You type "build a React login component" → the hook fires → Claude receives `🎯 INVOKE:frontend-engineer` → Claude launches the frontend-engineer agent with full specialist instructions.

---

## Prerequisites

- **Windows** with PowerShell 5.1+ (comes with Windows 10/11)
- **Claude Code** installed and working
- **VS Code** (optional, for task integration)
- An **existing project** with a `.claude/` folder, OR a new project where you want to set up the framework

---

## What's In This Package

```
framework-3.0/
├── CLAUDE.md                              ← Claude reads this every session
├── QUICKREF.md                            ← Your daily cheat sheet
├── SETUP.md                               ← You are here
├── .claude/
│   ├── settings.json                      ← Hook wiring + preferences
│   ├── agents/
│   │   └── _registry.json                 ← Maps agent names to file paths
│   ├── hooks/
│   │   ├── agent-router.ps1               ← Picks the right agent for your prompt
│   │   ├── skill-router.ps1               ← Loads skills based on file types
│   │   ├── conformance-gate.ps1           ← Catches mock data, TODOs, secrets
│   │   └── token-tracker.ps1              ← Monitors tool usage
│   └── skills/
│       ├── _registry.json                 ← Skill metadata
│       ├── python-development/SKILL.md    ← Python patterns + conventions
│       ├── typescript-development/SKILL.md ← TypeScript patterns + conventions
│       └── testing-best-practices/SKILL.md ← Testing patterns + conventions
└── .vscode/
    └── tasks.json                         ← VS Code task shortcuts
```

### What's NOT In This Package (You Provide These)

The **agent instruction files** (the actual `.md` files that tell each agent how to behave). These live in subdirectories like:

```
.claude/agents/
├── 00-product/product-manager.md
├── 01-language-specialists/python-expert.md
├── 01-language-specialists/typescript-expert.md
├── 01-language-specialists/terraform-expert.md
├── 02-role-specialists/frontend-engineer.md
├── 02-role-specialists/backend-engineer.md
├── 02-role-specialists/fullstack-engineer.md
├── 03-architecture/system-architect.md
├── 03-architecture/api-designer.md
├── 03-architecture/ui-designer.md
├── 04-quality/test-architect.md
├── 04-quality/qa-engineer.md
├── 04-quality/code-reviewer.md
├── 04-quality/security-auditor.md
├── 05-infrastructure/devops-engineer.md
├── 06-documentation/technical-writer.md
├── 07-troubleshooting/debugger.md
└── 07-troubleshooting/performance-optimizer.md
```

If you're coming from **Boiler 2.0**, you already have these. If you're starting fresh, you'll need to create them or use your own agent definitions.

---

## Setup: New Project (No Existing .claude/ Folder)

Open PowerShell. Navigate to your project root.

### Step 1: Copy Everything

```powershell
# Replace the path below with wherever you extracted the zip
$source = "$HOME\Downloads\framework-3.0"

# Copy framework files to your project root
Copy-Item "$source\CLAUDE.md" "."
Copy-Item "$source\QUICKREF.md" "."

# Copy the entire .claude folder
Copy-Item -Recurse "$source\.claude" "."

# Copy VS Code tasks (optional)
Copy-Item -Recurse "$source\.vscode" "."
```

### Step 2: Add Your Agent Files

Create the agent subdirectories and add your agent `.md` files:

```powershell
mkdir .claude\agents\00-product
mkdir .claude\agents\01-language-specialists
mkdir .claude\agents\02-role-specialists
mkdir .claude\agents\03-architecture
mkdir .claude\agents\04-quality
mkdir .claude\agents\05-infrastructure
mkdir .claude\agents\06-documentation
mkdir .claude\agents\07-troubleshooting
```

Then place your agent `.md` files in the matching directories. The `_registry.json` already has the correct paths mapped.

### Step 3: Allow PowerShell Scripts to Run

```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope CurrentUser
```

### Step 4: Edit CLAUDE.md Placeholders

Open `CLAUDE.md` in your editor. Find and replace these placeholders with your project info:

| Placeholder | Replace With | Example |
|------------|--------------|---------|
| `{{PROJECT_NAME}}` | Your project name | `IHMS` |
| `{{PROJECT_DESCRIPTION}}` | One-line description | `Home services management platform` |
| `{{TECH_STACK}}` | Your tech stack | `Next.js, TypeScript, Prisma, PostgreSQL` |
| `{{DEV_COMMAND}}` | How to start dev server | `npm run dev` |
| `{{TEST_COMMAND}}` | How to run tests | `npm run test` |
| `{{TYPECHECK_COMMAND}}` | How to type-check | `npx tsc --noEmit` |
| `{{LINT_COMMAND}}` | How to lint | `npm run lint` |

### Step 5: Verify

```powershell
# Test the agent router
echo "build a React login component" | powershell -ExecutionPolicy Bypass -NoProfile -File .claude/hooks/agent-router.ps1
```

You should see:
```
╔═══════════════════════════════════════════════════════════════╗
║ 🎯 INVOKE:frontend-engineer (confidence:185)
║
║ DIRECTIVE: Use Task(subagent_type="frontend-engineer")
║ DO NOT substitute with Explore/Plan
║ DO NOT work directly - launch the agent
╚═══════════════════════════════════════════════════════════════╝
```

**Done.** Open Claude Code in your project and start prompting.

---

## Setup: Existing Project (Already Has .claude/ Folder)

This is for projects already using Boiler 2.0 or a prior framework version. You're keeping your existing agents, skills, settings, and docs — and layering in the new hooks and registry.

Open PowerShell. Navigate to your project root.

### Step 1: Backup (Safety Net)

```powershell
Copy-Item -Recurse ".\.claude\hooks" ".\.claude\hooks_backup"
```

### Step 2: Copy New Hooks (4 files)

```powershell
$source = "$HOME\Downloads\framework-3.0"

Copy-Item -Force "$source\.claude\hooks\agent-router.ps1" ".\.claude\hooks\"
Copy-Item -Force "$source\.claude\hooks\skill-router.ps1" ".\.claude\hooks\"
Copy-Item -Force "$source\.claude\hooks\conformance-gate.ps1" ".\.claude\hooks\"
Copy-Item -Force "$source\.claude\hooks\token-tracker.ps1" ".\.claude\hooks\"
```

### Step 3: Copy Agent Registry (1 file)

```powershell
Copy-Item -Force "$source\.claude\agents\_registry.json" ".\.claude\agents\"
```

This file maps the 18 agent names to your existing agent file paths. It does NOT replace any of your agent `.md` files.

### Step 4: Copy Skill Files (4 files)

```powershell
# Create skill dirs if they don't exist
mkdir -Force ".\.claude\skills\python-development"
mkdir -Force ".\.claude\skills\typescript-development"
mkdir -Force ".\.claude\skills\testing-best-practices"

Copy-Item -Force "$source\.claude\skills\_registry.json" ".\.claude\skills\"
Copy-Item -Force "$source\.claude\skills\python-development\SKILL.md" ".\.claude\skills\python-development\"
Copy-Item -Force "$source\.claude\skills\typescript-development\SKILL.md" ".\.claude\skills\typescript-development\"
Copy-Item -Force "$source\.claude\skills\testing-best-practices\SKILL.md" ".\.claude\skills\testing-best-practices\"
```

If you already have skill folders with content you want to keep, skip the ones you want to preserve.

### Step 5: Copy Root Files (2 files)

```powershell
Copy-Item -Force "$source\CLAUDE.md" "."
Copy-Item -Force "$source\QUICKREF.md" "."
```

### Step 6: Copy VS Code Tasks (1 file, optional)

```powershell
mkdir -Force ".\.vscode"
Copy-Item -Force "$source\.vscode\tasks.json" ".\.vscode\"
```

If you have an existing `.vscode\tasks.json`, open both files and manually merge the task entries instead of overwriting.

### Step 7: Merge settings.json (MANUAL — DO NOT OVERWRITE)

This is the one file you **must merge by hand**. Your existing `settings.json` has your MCPs, permissions, and project-specific config.

Open your existing `.claude\settings.json` in your editor. Add these blocks from the framework's `settings.json`:

**Add the `hooks` block** (this is the critical one that wires everything together):

```json
"hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "command": "powershell -ExecutionPolicy Bypass -NoProfile -File .claude/hooks/agent-router.ps1",
            "type": "command"
          },
          {
            "command": "powershell -ExecutionPolicy Bypass -NoProfile -File .claude/hooks/skill-router.ps1",
            "type": "command"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matchers": [
          {
            "patterns": ["Write*", "Edit*", "Create*"]
          }
        ],
        "hooks": [
          {
            "command": "powershell -ExecutionPolicy Bypass -NoProfile -File .claude/hooks/conformance-gate.ps1",
            "type": "command"
          }
        ]
      },
      {
        "matchers": [
          {
            "patterns": ["*"]
          }
        ],
        "hooks": [
          {
            "command": "powershell -ExecutionPolicy Bypass -NoProfile -File .claude/hooks/token-tracker.ps1",
            "type": "command"
          }
        ]
      }
    ]
  }
```

**Add the `tokenOptimization` block**:

```json
"tokenOptimization": {
    "lazyLoadAgents": true,
    "lazyLoadSkills": true,
    "maxSkillsPerSession": null,
    "compactHookOutput": true
  }
```

**Add the `customInstructions`** (or append to your existing one):

```json
"customInstructions": "CRITICAL: When hooks output 'INVOKE:agent-name', you MUST use Task(subagent_type='agent-name'). Never substitute. When hooks output 'LOAD:skill-name', read SKILL.md FIRST. See CLAUDE.md for full framework."
```

### Step 8: Delete Old Hooks (Boiler 2.0 Leftovers)

These are superseded by the new hooks and should be removed:

```powershell
Remove-Item -ErrorAction SilentlyContinue ".\.claude\hooks\agent-activation-prompt.ps1"
Remove-Item -ErrorAction SilentlyContinue ".\.claude\hooks\skill-activation-prompt.ps1"
Remove-Item -ErrorAction SilentlyContinue ".\.claude\hooks\post-tool-use-tracker.ps1"
Remove-Item -ErrorAction SilentlyContinue ".\.claude\hooks\requirement-conformance-check.ps1"
```

### Step 9: Edit CLAUDE.md Placeholders

Same as Step 4 in the New Project section above. Replace `{{PROJECT_NAME}}`, `{{TECH_STACK}}`, etc.

### Step 10: Allow PowerShell Scripts + Verify

```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope CurrentUser

# Test
echo "build a React login component" | powershell -ExecutionPolicy Bypass -NoProfile -File .claude/hooks/agent-router.ps1
```

You should see the `🎯 INVOKE:frontend-engineer` directive box.

### Step 11: Delete Backup (When Satisfied)

```powershell
Remove-Item -Recurse ".\.claude\hooks_backup"
```

---

## How It Works

```
You type a prompt
       │
       ▼
┌─────────────────────────┐
│  agent-router.ps1       │  Reads your prompt, scores 18 agents,
│  (runs before Claude)   │  picks the best match, outputs INVOKE directive.
│                         │  If nothing matches → falls back to fullstack-engineer.
└─────────────────────────┘
       │
       ▼
┌─────────────────────────┐
│  skill-router.ps1       │  Checks what files are in your project,
│  (runs before Claude)   │  loads matching skill files (Python, TS, testing).
└─────────────────────────┘
       │
       ▼
┌─────────────────────────┐
│  Claude receives:       │  Your original prompt
│                         │  + "INVOKE:frontend-engineer"
│                         │  + "LOAD:typescript-development"
│                         │
│  Claude MUST:           │  1. Launch the named agent
│                         │  2. Read the skill file first
│                         │  3. Then do the work
└─────────────────────────┘
       │
       ▼
┌─────────────────────────┐
│  conformance-gate.ps1   │  After Claude writes/edits any file,
│  (runs after each tool) │  scans for mock data, TODOs, hardcoded
│                         │  secrets, console.logs in production code.
└─────────────────────────┘
       │
       ▼
┌─────────────────────────┐
│  token-tracker.ps1      │  Logs every tool call to .claude/logs/.
│  (runs after each tool) │  Alerts at 50 and 100 tool calls.
└─────────────────────────┘
```

---

## The 18 Agents

| Agent | When It Fires | What It Does |
|-------|--------------|-------------|
| **product-manager** | "requirements", "PRD", "user story" | Defines what to build |
| **system-architect** | "architecture", "system design", "scale" | Designs system structure |
| **api-designer** | "API design", "REST", "GraphQL" | Designs API contracts |
| **ui-designer** | "UI design", "wireframe", "mockup" | Creates design specs |
| **frontend-engineer** | "React", "component", "frontend" | Builds UI |
| **backend-engineer** | "backend", "database", "server" | Builds services |
| **fullstack-engineer** | "fullstack", "end-to-end" + **fallback** | Full features |
| **python-expert** | "python", "django", "fastapi" | Python development |
| **typescript-expert** | "typescript", "react", "next.js" | TypeScript development |
| **terraform-expert** | "terraform", ".tf", "IaC" | Infrastructure as code |
| **test-architect** | "test strategy", "test pyramid" | Designs test approach |
| **qa-engineer** | "write tests", "test this", "coverage" | Writes actual tests |
| **code-reviewer** | "review", "PR", "code quality" | Reviews code |
| **security-auditor** | "security", "vulnerability", "OWASP" | Security review |
| **devops-engineer** | "CI/CD", "deploy", "docker" | DevOps + infra |
| **technical-writer** | "documentation", "README", "docs" | Writes docs |
| **debugger** | "bug", "error", "broken", "not working" | Troubleshooting |
| **performance-optimizer** | "slow", "optimize", "bottleneck" | Performance tuning |

**Fallback**: If your prompt doesn't match any agent above a confidence of 70, `fullstack-engineer` activates automatically. Every prompt gets an agent.

---

## VS Code Tasks (Optional)

If you copied `.vscode/tasks.json`, you get these in VS Code via `Ctrl+Shift+P` → "Run Task":

| Task | What It Does |
|------|-------------|
| `Claude: Validate Framework` | Checks all hooks and files are present |
| `Claude: Test Agent Router` | Runs sample prompts through the router |
| `Claude: Test Skill Router` | Tests skill detection |
| `Claude: View Session Stats` | Shows tool usage logs |
| `Claude: Clear Session` | Resets session state |

---

## Troubleshooting

### "Hooks aren't firing"

1. Check execution policy:
   ```powershell
   Get-ExecutionPolicy -List
   ```
   `CurrentUser` should show `Bypass`.

2. Test hook manually:
   ```powershell
   echo "debug this error" | powershell -ExecutionPolicy Bypass -NoProfile -File .claude/hooks/agent-router.ps1
   ```

3. Verify `settings.json` has the `hooks` block (Step 7 above).

### "Agent not found" or wrong agent loads

1. Check `_registry.json` paths match your actual agent file locations.
2. Test with explicit trigger words:
   ```powershell
   echo "review this code for security vulnerabilities" | powershell -ExecutionPolicy Bypass -NoProfile -File .claude/hooks/agent-router.ps1
   ```
   Should show `security-auditor`, not `code-reviewer`.

### "Claude ignores the directive"

The directive system uses strong framing but Claude can still occasionally ignore it. If this happens:
- Re-run the prompt (hooks will re-fire)
- Add "use the [agent-name] agent" to your prompt as reinforcement
- Check that `customInstructions` is in your `settings.json`

### "Conformance gate has false positives"

Edit `.claude/hooks/conformance-gate.ps1` to adjust patterns. Common fix:
- Add file exclusions for test files, fixtures, or seed data

---

## Customization

### Add a New Agent

1. Create the agent `.md` file in the appropriate `.claude/agents/` subdirectory
2. Add an entry to `.claude/agents/_registry.json`
3. Add scoring patterns to `.claude/hooks/agent-router.ps1` (follow the existing pattern)

### Add a New Skill

1. Create `.claude/skills/your-skill/SKILL.md`
2. Add an entry to `.claude/skills/_registry.json`
3. Add file detection patterns to `.claude/hooks/skill-router.ps1`

### Adjust Agent Sensitivity

In `agent-router.ps1`:
- **Line 305**: `$ConfidenceThreshold = 70` — lower = more agents fire, higher = fewer
- Individual trigger scores can be adjusted per agent block
- Anti-patterns subtract points to prevent false positives

---

## File Summary

| File | You Touch? | Purpose |
|------|-----------|---------|
| `CLAUDE.md` | **YES** — fill in placeholders | Claude's primary instruction file |
| `QUICKREF.md` | No | Your reference card |
| `SETUP.md` | No | This guide |
| `.claude/settings.json` | **YES** — merge into existing | Wires hooks to Claude Code |
| `.claude/hooks/*.ps1` | Only to customize | 4 automation scripts |
| `.claude/agents/_registry.json` | Only if paths differ | Maps agent names → files |
| `.claude/agents/**/*.md` | These are YOURS | Agent instruction files |
| `.claude/skills/_registry.json` | Only to add skills | Skill metadata |
| `.claude/skills/**/SKILL.md` | Only to customize | Skill instruction files |
| `.vscode/tasks.json` | Optional | VS Code shortcuts |
