# Framework 3.0 Quick Reference

## Hook Output → Action Required

| Hook Output | Claude MUST Do |
|-------------|----------------|
| `🎯 INVOKE:agent-name` | `Task(subagent_type="agent-name")` |
| `📚 LOAD:skill-name` | Read `.claude/skills/skill-name/SKILL.md` |
| `🚨 VIOLATION: ...` | Fix issue before marking complete |
| `⚠️ WARNING: ...` | Address or acknowledge |

## Agent Routing

| User Says | Agent Invoked |
|-----------|---------------|
| "build a component" | `frontend-engineer` |
| "create an API" | `backend-engineer` |
| "end-to-end feature" | `fullstack-engineer` |
| "debug this error" | `debugger` |
| "write tests" | `qa-engineer` |
| "test strategy" | `test-architect` |
| "review this code" | `code-reviewer` |
| "security audit" | `security-auditor` |
| "define requirements" | `product-manager` |
| "system architecture" | `system-architect` |

## Pre-Implementation Checklist
```
□ Read PRD completely
□ Create TodoWrite with ALL acceptance criteria
□ Identify integration points (UI → API → DB)
□ If Large/XL scope → Propose phasing FIRST
```

## Pre-Completion Checklist
```
□ All acceptance criteria pass
□ UI connects to real API (no mocks)
□ API connects to real database (no stubs)
□ Error handling works
□ Loading states work
□ TodoWrite is 100% complete
```

## Forbidden Actions
- ❌ Create UI without backend connection
- ❌ Use mock data without explicit TODO
- ❌ Skip acceptance criteria without approval
- ❌ Mark "complete" with issues remaining
- ❌ Substitute generic agents when specific one is invoked

## Token Optimization
- Agents load on-demand (not always)
- Skills load only when files detected
- Session reminders shown once per session
- Hook output is compact

## VS Code Tasks
- `Ctrl+Shift+P` → `Run Task`
- `Claude: Validate Framework` - Check setup
- `Claude: Test Agent Router` - Test routing
- `Claude: Clear Session` - Reset state

## Troubleshooting
```powershell
# Test hook manually
echo "build a react component" | .\.claude\hooks\agent-router.ps1

# Check execution policy
Get-ExecutionPolicy -List

# Enable if needed
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope CurrentUser
```

## File Locations
```
CLAUDE.md                    # Read first, always
.claude/settings.json        # Hook configuration
.claude/hooks/               # Execution hooks
.claude/agents/              # Agent instructions
.claude/skills/              # Skill instructions
.claude/logs/                # Usage logs
```
