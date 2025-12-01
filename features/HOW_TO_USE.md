# Agentic Coding Patterns - Usage Guide

```
  Documentation:
  - HOW_TO_USE.md - Comprehensive guide to agentic coding patterns (15KB)

  Slash Commands (.claude/commands/):
  | Command            | File                 | Purpose                                     |
  |--------------------|----------------------|---------------------------------------------|
  | /plan              | plan.md              | Interview user, create Job→Task breakdown   |
  | /orchestrate       | orchestrate.md       | Execute job with parallel workers           |
  | /qc                | qc.md                | Quality check candidates, build score table |
  | /finalize          | finalize.md          | Move winner, cleanup                        |
  | /retry-until-green | retry-until-green.md | Retry single task until QC passes           |
  | /cleanup           | cleanup.md           | Reset orchestration state                   |

  Agent Configurations (.claude/agents/):
  | Agent   | File       | Model   | Role                               |
  |---------|------------|---------|------------------------------------|
  | Planner | planner.md | Sonnet  | Strategic planning, user interview |
  | Worker  | worker.md  | ZAI/GLM | Implementation execution           |
  | QC      | qc.md      | Sonnet  | Quality assessment, scoring        |

  Updated:
  - CLAUDE.md - Added "Agentic Coding Patterns" section with quick reference

  Architecture

  User → /plan → Planner (Sonnet)
                      ↓
                 job.json
                      ↓
         /orchestrate → Orchestrator (Sonnet)
                      ↓
      ┌───────────────┼───────────────┐
      ↓               ↓               ↓
  Worker 1        Worker 2        Worker 3  (ZAI/GLM)
      ↓               ↓               ↓
  candidates/     candidates/     candidates/
      └───────────────┼───────────────┘
                      ↓
                /qc → QC Agent (Sonnet)
                      ↓
              Score table + Winner
                      ↓
          /finalize → Move to final location

```

## Overview

This project implements **redundant worker patterns** for AI-assisted coding. With flat-rate/free AI workers (ZAI/GLM profile), the optimal strategy shifts from "get it right first time" to "run multiple workers and pick the best".

## Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│ USER                                                                        │
│   Invokes: /plan-feature "Add dark mode toggle"                            │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ PLANNER (Sonnet)                              .claude/commands/plan.md     │
│   - Interviews user via AskUserQuestion                                    │
│   - Creates Job → Task breakdown                                           │
│   - Identifies sequential vs parallel work                                 │
│   - Applies SOLID principles                                               │
│   - Outputs: job.json with task definitions                                │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ ORCHESTRATOR (Sonnet)                    .claude/commands/orchestrate.md   │
│   - Reads job.json                                                         │
│   - Creates candidates/ directory structure                                │
│   - Dispatches N workers per task (parallel)                               │
│   - Monitors completion                                                    │
│   - Triggers QC on candidates                                              │
│   - Selects winners, cleans up                                             │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ WORKER 1     │ │ WORKER 2     │ │ WORKER 3     │    .claude/agents/worker.md
│ (ZAI/GLM)    │ │ (ZAI/GLM)    │ │ (ZAI/GLM)    │
│              │ │              │ │              │
│ candidates/  │ │ candidates/  │ │ candidates/  │
│ worker_1/    │ │ worker_2/    │ │ worker_3/    │
└──────────────┘ └──────────────┘ └──────────────┘
                    │               │               │
                    └───────────────┼───────────────┘
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ QC AGENT (Sonnet)                               .claude/agents/qc.md       │
│   - Runs lint, typecheck on each candidate                                 │
│   - Scores code quality                                                    │
│   - Builds comparison table                                                │
│   - Recommends winner or asks user                                         │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ FINALIZER                                  .claude/commands/finalize.md    │
│   - Moves winner to final location                                         │
│   - Cleans up candidates/                                                  │
│   - Updates job status                                                     │
└────────────────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
.claude/
├── commands/                    # Slash commands (user-invokable)
│   ├── plan.md                  # /plan - Interview user, create Job→Task breakdown
│   ├── orchestrate.md           # /orchestrate - Run workers, manage candidates
│   ├── qc.md                    # /qc - Quality check candidates
│   ├── finalize.md              # /finalize - Select winner, cleanup
│   ├── retry-until-green.md     # /retry-until-green - Retry until QC passes
│   └── cleanup.md               # /cleanup - Remove candidates, reset state
│
├── agents/                      # Subagent configurations
│   ├── planner.md               # Planning agent (Sonnet)
│   ├── worker.md                # Implementation worker (ZAI/GLM)
│   └── qc.md                    # Quality control agent (Sonnet)
│
└── settings.local.json          # Local overrides (profiles, etc.)

candidates/                      # Work directory (created during orchestration)
├── worker_1/
│   └── <generated files>
├── worker_2/
│   └── <generated files>
└── worker_3/
    └── <generated files>

job.json                         # Current job definition (created by /plan)
```

## Slash Commands

### /plan [feature-description]

**Purpose**: Interview user and create a Job→Task breakdown.

**Process**:
1. Asks clarifying questions (frontend/backend split, tech choices)
2. Identifies dependencies between tasks
3. Marks tasks as sequential or parallel
4. Applies SOLID principles to structure
5. Creates `job.json` with full breakdown

**Example**:
```bash
/plan "Add user authentication with OAuth"
```

**Output**: `job.json`
```json
{
  "name": "Add OAuth Authentication",
  "description": "Implement OAuth2 login flow",
  "tasks": [
    {
      "id": "1",
      "name": "Create auth models",
      "type": "backend",
      "parallel_group": 1,
      "prompt": "Create user and session models...",
      "workers": 3
    },
    {
      "id": "2",
      "name": "Create auth endpoints",
      "type": "backend",
      "parallel_group": 1,
      "depends_on": ["1"],
      "prompt": "Create login/logout endpoints...",
      "workers": 3
    }
  ]
}
```

### /orchestrate [job-file]

**Purpose**: Execute the job, managing parallel workers.

**Process**:
1. Reads `job.json` (or specified file)
2. Creates `candidates/` directory
3. For each task (respecting dependencies):
   - Creates `candidates/task_{id}/worker_{n}/` directories
   - Spawns N workers in parallel (via scheduler API)
   - Polls for completion
4. Triggers `/qc` for each task
5. Moves winners to final locations

**Example**:
```bash
/orchestrate job.json
```

### /qc [candidates-dir]

**Purpose**: Quality check candidate implementations.

**Process**:
1. Lists all worker directories in candidates/
2. For each candidate:
   - Runs `make lint`
   - Runs `make typecheck`
   - Counts LOC
   - Checks for docstrings
3. Builds comparison table
4. If clear winner: auto-selects
5. If tie: asks user to choose
6. If all fail: reports and suggests retry

**Example**:
```bash
/qc candidates/task_1/
```

**Output**:
```
| Worker   | Lint | Type | LOC | Docs | Score |
|----------|------|------|-----|------|-------|
| worker_1 | PASS | PASS | 245 | 8/10 | 18    |
| worker_2 | FAIL | PASS | 312 | 6/10 | 10    |
| worker_3 | PASS | PASS | 198 | 9/10 | 19    | ← WINNER

Recommendation: worker_3 (highest score)
Proceed with selection? [Y/n]
```

### /finalize [winner] [destination]

**Purpose**: Move winner to final location, cleanup.

**Process**:
1. Copies winner files to destination
2. Removes `candidates/` directory
3. Updates `job.json` status
4. Commits changes (optional)

**Example**:
```bash
/finalize candidates/task_1/worker_3 claude_code_scheduler/cli_tasks.py
```

### /retry-until-green [task-description]

**Purpose**: Run a single task, retry until QC passes.

**Process**:
1. Runs worker with task
2. Runs QC (lint + typecheck)
3. If pass: done
4. If fail: delete output, retry (max 5 attempts)

**Example**:
```bash
/retry-until-green "Create cli_tasks.py with CRUD operations"
```

### /cleanup

**Purpose**: Remove all candidates and reset state.

**Process**:
1. Removes `candidates/` directory
2. Removes `job.json`
3. Cleans up temporary scheduler tasks

**Example**:
```bash
/cleanup
```

## Agents

### Planner Agent (Sonnet)

**Role**: Strategic planning and user interview.

**Capabilities**:
- Uses AskUserQuestion for clarification
- Understands SOLID principles
- Can identify frontend/backend split
- Creates optimal task sequencing

**Invoked by**: `/plan` command

### Worker Agent (ZAI/GLM)

**Role**: Implementation execution.

**Capabilities**:
- Writes code to specified directory
- Follows CLAUDE.md conventions
- Works in isolation (no cross-worker communication)

**Profile**: `5270805b-3731-41da-8710-fe765f2e58be` (ZAI)

**Invoked by**: `/orchestrate` command

### QC Agent (Sonnet)

**Role**: Quality assessment and selection.

**Capabilities**:
- Runs static analysis tools
- Compares code quality metrics
- Makes selection recommendations

**Invoked by**: `/qc` command

## Workflow Examples

### Example 1: Simple Feature

```bash
# 1. Plan the feature
/plan "Add --json output flag to CLI commands"

# 2. Review job.json, adjust if needed

# 3. Execute with redundant workers
/orchestrate

# 4. Review QC results, select winners

# 5. Finalize (auto-triggered by orchestrate, or manual)
/finalize
```

### Example 2: Complex Feature with Dependencies

```bash
# 1. Plan with interview
/plan "Implement job management with cascade delete"

# Planner asks:
# - "Should jobs have their own REST API endpoints?" → Yes
# - "Should the UI show jobs in a separate panel?" → Yes
# - "Database: JSON files or SQLite?" → JSON files

# 2. Review generated job.json
# Shows: Phase 1 (models) → Phase 2 (API, CLI parallel) → Phase 3 (UI)

# 3. Execute
/orchestrate

# Workers run:
# - Phase 1: 3 workers on models (parallel)
# - QC selects winner
# - Phase 2: 3 workers on API, 3 on CLI (parallel)
# - QC selects winners
# - Phase 3: 3 workers on UI (parallel)
# - QC selects winner

# 4. All winners moved to final locations
# 5. Cleanup automatic
```

### Example 3: Retry Until Green

```bash
# Single file, well-defined success criteria
/retry-until-green "Create cli_jobs.py with list/get/create/delete commands. Must pass make lint && make typecheck."

# Attempt 1: lint fails (missing type hints)
# Attempt 2: typecheck fails (wrong return type)
# Attempt 3: PASS - done!
```

## Configuration

### Profile Setup

Ensure ZAI profile exists in scheduler:
```bash
curl http://127.0.0.1:5679/api/profiles
```

Expected profile for workers:
```json
{
  "id": "5270805b-3731-41da-8710-fe765f2e58be",
  "name": "ZAI",
  "env_vars": [
    {"name": "ANTHROPIC_AUTH_TOKEN", "source": "keychain", "value": "zai-api-key"},
    {"name": "ANTHROPIC_BASE_URL", "source": "static", "value": "https://api.z.ai/api/anthropic"},
    {"name": "CLAUDE_CODE_USE_BEDROCK", "source": "static", "value": "0"}
  ]
}
```

### Worker Count

Default: 3 workers per task.

Override in `job.json`:
```json
{
  "tasks": [
    {
      "name": "Critical component",
      "workers": 5
    }
  ]
}
```

### QC Thresholds

In `.claude/settings.local.json`:
```json
{
  "qc": {
    "auto_select_threshold": 15,
    "lint_required": true,
    "typecheck_required": true,
    "min_doc_score": 6
  }
}
```

## Best Practices

### 1. Clear Task Boundaries

Good:
```json
{"name": "Create cli_tasks.py", "prompt": "Create CRUD commands for tasks API..."}
```

Bad:
```json
{"name": "Implement CLI", "prompt": "Make the CLI work..."}
```

### 2. Explicit Output Paths

Always specify where workers should write:
```
Write output to: ./candidates/worker_{id}/cli_tasks.py
```

### 3. Include Context

Workers don't see each other. Include relevant context:
```
Reference files:
- cli_client.py (HTTP client pattern)
- cli_runs.py (similar CLI structure)
- CLAUDE.md (conventions)
```

### 4. Sequential When Needed

If Task B depends on Task A's output, mark as sequential:
```json
{
  "id": "2",
  "depends_on": ["1"],
  "parallel_group": 2
}
```

### 5. QC is the Bottleneck

With free workers, you can run 10 in parallel. But QC still takes time.
- Automate QC where possible (lint, typecheck, tests)
- Reserve human judgment for architectural decisions

## Troubleshooting

### Workers Not Starting

Check scheduler is running:
```bash
curl http://127.0.0.1:5679/api/health
```

Check ZAI profile:
```bash
curl http://127.0.0.1:5679/api/profiles
```

### All Candidates Fail QC

1. Review the prompt - is it clear enough?
2. Check CLAUDE.md conventions - are they documented?
3. Try `/retry-until-green` with more specific instructions
4. Consider Pipeline pattern: Create → Review → Fix

### Candidates Diverge Too Much

Add constraints to prompt:
```
Requirements:
- Use httpx for HTTP client
- Follow existing cli_runs.py structure
- Use tabulate for table output
```

### Cleanup Failed

Manual cleanup:
```bash
rm -rf ./candidates/
rm -f ./job.json
curl http://127.0.0.1:5679/api/tasks | jq '.tasks[] | select(.name | startswith("worker-"))'
# Delete each temporary task
```
