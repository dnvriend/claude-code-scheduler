# Troubleshooting Reference

## Common Issues

### Z.AI / GLM Profile Not Working

**Symptom:** Task fails with "Invalid API Key format" or authentication errors when using Z.AI profile.

**Cause:** `CLAUDE_CODE_USE_BEDROCK=1` is set in the shell environment, which overrides the Z.AI authentication.

**Solution:** Ensure the Z.AI profile sets `CLAUDE_CODE_USE_BEDROCK=0` (or unsets it entirely).

**Key env vars for Z.AI:**
```bash
ANTHROPIC_AUTH_TOKEN=<z.ai-token>
ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic
CLAUDE_CODE_USE_BEDROCK=0  # Must be 0 for Z.AI!
```

### Empty Env Vars Breaking Auth

**Symptom:** Authentication fails even though profile has correct values.

**Cause:** Empty env vars (e.g., `ANTHROPIC_API_KEY=`) override valid auth tokens.

**Solution:** The scheduler now skips empty values automatically. Check logs for `ENV SKIP:` warnings.

### Workers Not Starting

**Check scheduler is running:**
```bash
curl http://127.0.0.1:5679/api/health
```

**Check ZAI profile exists:**
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

### Port Already in Use

**Check what's using the port:**
```bash
lsof -i :5679  # GUI debug port
lsof -i :8787  # Daemon port
```

**Kill processes using ports:**
```bash
lsof -ti:5679 | xargs kill -9
lsof -ti:8787 | xargs kill -9
```

### Command Not Found

**Verify installation:**
```bash
claude-code-scheduler --version
```

**Reinstall:**
```bash
uv tool install . --reinstall
```

### GUI Not Starting

**Check PyQt6 is installed:**
```bash
uv pip list | grep PyQt6
```

**Try with verbose logging:**
```bash
claude-code-scheduler gui -vvv
```

### REST API Connection Refused

**GUI must be running:**
```bash
claude-code-scheduler gui &
sleep 2
curl http://127.0.0.1:5679/api/health
```

**Check correct port:**
```bash
claude-code-scheduler gui --restport 5679
```

### Task Stuck in Running State

**Stop the task:**
```bash
curl -X POST http://127.0.0.1:5679/api/runs/{run-id}/stop
```

**Check runs:**
```bash
claude-code-scheduler cli runs list --output table
```

### Import Fails with UUID Conflict

**Error:** Job with UUID already exists

**Solution:** Use `--force` to overwrite:
```bash
claude-code-scheduler cli jobs import --input job.json --force
```

### Import Fails with Missing Profile

**Error:** Profile not found

**Solution:** Create the profile first or check available profiles:
```bash
curl http://127.0.0.1:5679/api/profiles
```

## Debug Mode

In GUI Settings dialog or `settings.json`:

| Setting | Effect |
|---------|--------|
| `mock_mode: true` | Simulate CLI execution (no real Claude calls) |
| `unmask_env_vars: true` | Show full env var values in debug logs |

## Manual Cleanup

```bash
# Remove candidates directory
rm -rf ./candidates/

# Remove job.json
rm -f ./job.json

# Find and delete temporary tasks
curl http://127.0.0.1:5679/api/tasks | jq '.tasks[] | select(.name | startswith("worker-"))'
```

## Log Locations

```
~/.claude-scheduler/logs/
└── run_<uuid>.log   # Per-run output logs
```

**View run log:**
```bash
claude-code-scheduler debug log <run-id>
```

## Getting Help

```bash
# Show help
claude-code-scheduler --help

# Command-specific help
claude-code-scheduler cli tasks --help
claude-code-scheduler debug --help
```

## Port Administration

See [PORTS.md](../../PORTS.md) for complete port allocation.

**Quick Reference:**
| Port | Service |
|------|---------|
| 5679 | GUI debug server |
| 8787 | Daemon HTTP API |

**Reserved ranges:** 5679-5689, 8787-8797 (for multi-environment testing)
