# Claude Code Execution Framework 3.0

## 🎯 CRITICAL DIRECTIVES (Read First, Execute Always)

### Directive 1: Agent Activation is MANDATORY
When `.claude/hooks/agent-router.ps1` outputs `🎯 INVOKE:agent-name`, you MUST:
1. **Immediately** use `Task(subagent_type="agent-name", ...)` for complex work
2. **Never** substitute with Explore/Plan when a specific agent is named
3. **Never** work directly when an agent is designated
4. If confidence shows "fallback", fullstack-engineer is the default — still INVOKE it

### Directive 2: Skill Loading is AUTOMATIC
When `.claude/hooks/skill-router.ps1` outputs `📚 LOAD:skill-name`:
- Read `.claude/skills/skill-name/SKILL.md` BEFORE implementation
- Skills contain domain-specific patterns that reduce errors by 80%
- All relevant skills load — no cap on number of skills per session

### Directive 3: Zero Wireframe Tolerance
**BEFORE declaring any feature complete:**
```
✅ UI connects to real API (no mock data)
✅ API connects to real database (no stubs)  
✅ All acceptance criteria from PRD pass
✅ TodoWrite checklist is 100% complete
```
If ANY fails → STOP → Communicate constraint → Get approval

---

## 📁 Framework Structure

```
.claude/
├── agents/           # Specialist agents (load on-demand)
│   ├── _registry.json    # Agent metadata + trigger patterns
│   └── [agent].md        # Full agent instructions
├── hooks/            # Execution hooks (Windows PowerShell)
│   ├── agent-router.ps1      # Pre-prompt: Determines agent
│   ├── skill-router.ps1      # Pre-prompt: Loads skills
│   ├── conformance-gate.ps1  # Post-tool: Validates work
│   └── token-tracker.ps1     # Post-tool: Monitors usage
├── skills/           # Domain knowledge (load on-demand)
│   ├── _registry.json    # Skill metadata
│   └── [skill]/SKILL.md  # Skill instructions
├── commands/         # Slash commands
└── docs/             # Framework documentation
```

---

## 🔄 Execution Flow

```
User Prompt
    ↓
[Hook: agent-router.ps1] → Analyzes prompt → Outputs agent directive
    ↓
[Hook: skill-router.ps1] → Detects files → Outputs skill directive
    ↓
Claude receives: Original prompt + Agent directive + Skill directive
    ↓
Claude MUST:
  1. If agent directive present → Launch via Task tool
  2. If skill directive present → Read SKILL.md first
  3. Execute with full conformance
    ↓
[Hook: conformance-gate.ps1] → Validates outputs → Flags violations
    ↓
Complete or Iterate
```

---

## 🚨 Enforcement Rules

### Rule 1: Agent Priority
```
Hook says "INVOKE:test-architect" → You MUST use test-architect
You DO NOT get to choose Explore, Plan, or work directly
```

### Rule 2: Skill Priority  
```
Hook says "LOAD:python-development" → You MUST read SKILL.md
You DO NOT skip this step to "save time"
```

### Rule 3: Conformance Priority
```
PRD has 10 acceptance criteria → All 10 MUST pass
You DO NOT mark 8/10 as "complete"
```

---

## 🎛️ Agent Quick Reference

| Agent | Trigger Patterns | Use For |
|-------|------------------|---------|
| `product-manager` | requirements, PRD, user story | Defining what to build |
| `system-architect` | architecture, design, scale | How to structure systems |
| `api-designer` | API design, REST, GraphQL, OpenAPI | Designing API contracts |
| `ui-designer` | UI design, wireframe, mockup, prototype | UI/UX design specs |
| `frontend-engineer` | React, UI, component, CSS | Building interfaces |
| `backend-engineer` | API, database, server | Building services |
| `fullstack-engineer` | end-to-end, full feature | Complete features (DEFAULT FALLBACK) |
| `python-expert` | .py, django, fastapi | Python development |
| `typescript-expert` | .ts, React, Next.js | TypeScript development |
| `terraform-expert` | .tf, terraform, IaC | Infrastructure as code |
| `qa-engineer` | test, validate, coverage | Writing tests |
| `test-architect` | test strategy, test pyramid | Designing test approach |
| `code-reviewer` | review, PR, quality | Code review |
| `debugger` | bug, error, fix, broken | Troubleshooting |
| `performance-optimizer` | slow, optimize, profile | Performance tuning |
| `security-auditor` | security, vulnerability | Security review |
| `devops-engineer` | CI/CD, deploy, docker | Infrastructure |
| `technical-writer` | docs, README, explain | Documentation |

---

## 📋 Pre-Implementation Checklist

**BEFORE writing any code:**

- [ ] Read complete PRD/requirements
- [ ] Create TodoWrite with EVERY acceptance criterion
- [ ] Identify integration points (UI → API → DB)
- [ ] Load relevant skills via hook directives
- [ ] If scope is Large/XL → Propose phasing FIRST

---

## 📋 Pre-Completion Checklist

**BEFORE marking ANY feature complete:**

- [ ] All acceptance criteria pass
- [ ] No mock data in production code
- [ ] All APIs connected to real database
- [ ] All UI elements are functional (not just visual)
- [ ] Error handling works
- [ ] Loading states work
- [ ] TodoWrite is 100% done

---

## 🔧 Development Commands

```bash
# Start development
{{DEV_COMMAND}}

# Run tests
{{TEST_COMMAND}}

# Type check
{{TYPECHECK_COMMAND}}

# Lint
{{LINT_COMMAND}}
```

---

## 📚 Project Context

**Project**: {{PROJECT_NAME}}
**Description**: {{PROJECT_DESCRIPTION}}
**Stack**: {{TECH_STACK}}

---

## ⚡ Token Optimization

1. **Agents load on-demand**: Only read full agent.md when invoked
2. **Skills load on-demand**: Only read SKILL.md when relevant files detected
3. **Registry files are compact**: Metadata only, no full instructions
4. **Conformance is deferred**: Validation happens post-implementation, not pre

---

## 🎓 Decision Framework

```
Does this change scope or requirements?
├── YES → STOP → Ask user → Get approval
└── NO → Is this a standard implementation detail?
    ├── YES → Proceed with best practices
    └── NO → Reference loaded skill/agent → Proceed with documentation
```

---

**Framework Version**: 3.0
**Last Updated**: 2025-02-04
**Status**: Active
