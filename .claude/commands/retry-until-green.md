---
description: Retry a task until lint and typecheck pass
arguments:
  - name: task
    description: Task description/prompt for the worker
  - name: output_path
    description: Where to write the output file
  - name: max_attempts
    description: Maximum retry attempts (default: 5)
    default: "5"
---

# Retry Until Green

You are a **Sonnet Orchestrator** that retries a single task until QC passes.

## Your Role

1. **Run** a worker with the task
2. **QC** the output (lint + typecheck)
3. **If pass**: Done!
4. **If fail**: Delete output, retry with feedback
5. **Loop** until success or max attempts

## Input

- Task prompt: $ARGUMENTS.task
- Output path: $ARGUMENTS.output_path
- Max attempts: $ARGUMENTS.max_attempts

## Configuration

```
SCHEDULER_API: http://127.0.0.1:5679
ZAI_PROFILE_ID: 5270805b-3731-41da-8710-fe765f2e58be
```

## Process

### Initialization

```bash
ATTEMPT=0
MAX_ATTEMPTS=$ARGUMENTS.max_attempts
SUCCESS=false
LAST_ERRORS=""

# Create temp directory for this retry session
RETRY_DIR="./retry_$(date +%s)"
mkdir -p $RETRY_DIR
```

### Retry Loop

```bash
while [ $ATTEMPT -lt $MAX_ATTEMPTS ] && [ "$SUCCESS" = "false" ]; do
    ATTEMPT=$((ATTEMPT + 1))
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "  ATTEMPT $ATTEMPT / $MAX_ATTEMPTS"
    echo "═══════════════════════════════════════════════════════════"

    # Build prompt with feedback from previous attempt
    if [ -n "$LAST_ERRORS" ]; then
        WORKER_PROMPT=$(cat <<EOF
$ARGUMENTS.task

PREVIOUS ATTEMPT FAILED with these errors:
$LAST_ERRORS

FIX THESE ISSUES in your implementation.

Write output to: $RETRY_DIR/attempt_$ATTEMPT/
EOF
)
    else
        WORKER_PROMPT=$(cat <<EOF
$ARGUMENTS.task

Write output to: $RETRY_DIR/attempt_$ATTEMPT/
EOF
)
    fi

    mkdir -p $RETRY_DIR/attempt_$ATTEMPT/

    # Create and run worker task
    echo "  Dispatching worker..."

    TASK_RESPONSE=$(curl -s -X POST http://127.0.0.1:5679/api/tasks \
        -H "Content-Type: application/json" \
        -d '{
            "name": "retry-attempt-'$ATTEMPT'-'$(date +%s)'",
            "prompt": "'"$(echo "$WORKER_PROMPT" | sed 's/"/\\"/g' | tr '\n' ' ')"'",
            "model": "sonnet",
            "profile": "5270805b-3731-41da-8710-fe765f2e58be",
            "permissions": "bypass",
            "schedule": {"schedule_type": "manual"},
            "enabled": false
        }')

    TASK_ID=$(echo $TASK_RESPONSE | jq -r '.task.id')

    if [ "$TASK_ID" = "null" ] || [ -z "$TASK_ID" ]; then
        echo "  ERROR: Failed to create task"
        echo "  Response: $TASK_RESPONSE"
        continue
    fi

    # Run the task
    curl -s -X POST http://127.0.0.1:5679/api/tasks/$TASK_ID/run > /dev/null

    # Poll for completion
    echo "  Waiting for worker to complete..."
    TIMEOUT=600  # 10 minutes
    ELAPSED=0

    while [ $ELAPSED -lt $TIMEOUT ]; do
        RUNS=$(curl -s http://127.0.0.1:5679/api/runs)
        RUN_STATUS=$(echo $RUNS | jq -r ".runs[] | select(.task_id == \"$TASK_ID\") | .status" | head -1)

        if [ "$RUN_STATUS" = "success" ] || [ "$RUN_STATUS" = "failed" ]; then
            break
        fi

        sleep 10
        ELAPSED=$((ELAPSED + 10))
        echo "    ... $ELAPSED seconds elapsed"
    done

    if [ $ELAPSED -ge $TIMEOUT ]; then
        echo "  TIMEOUT: Worker did not complete in 10 minutes"
        curl -s -X DELETE http://127.0.0.1:5679/api/tasks/$TASK_ID > /dev/null
        LAST_ERRORS="Worker timeout - try simplifying the task"
        continue
    fi

    # Check if output exists
    OUTPUT_FILES=$(find $RETRY_DIR/attempt_$ATTEMPT/ -name "*.py" 2>/dev/null)
    if [ -z "$OUTPUT_FILES" ]; then
        echo "  ERROR: No Python files generated"
        LAST_ERRORS="No output files generated - ensure prompt specifies file creation"
        curl -s -X DELETE http://127.0.0.1:5679/api/tasks/$TASK_ID > /dev/null
        continue
    fi

    echo "  Output files: $(echo $OUTPUT_FILES | tr '\n' ' ')"

    # Run QC
    echo "  Running QC..."
    cd $RETRY_DIR/attempt_$ATTEMPT/

    LINT_OUTPUT=$(make lint 2>&1) || true
    LINT_EXIT=$?

    TYPE_OUTPUT=$(make typecheck 2>&1) || true
    TYPE_EXIT=$?

    cd - > /dev/null

    # Evaluate results
    if [ $LINT_EXIT -eq 0 ] && [ $TYPE_EXIT -eq 0 ]; then
        echo ""
        echo "  ✓ LINT: PASS"
        echo "  ✓ TYPECHECK: PASS"
        echo ""
        SUCCESS=true
    else
        echo ""
        if [ $LINT_EXIT -ne 0 ]; then
            echo "  ✗ LINT: FAIL"
            LINT_ERRORS=$(echo "$LINT_OUTPUT" | grep -E "error|Error" | head -10)
        else
            echo "  ✓ LINT: PASS"
            LINT_ERRORS=""
        fi

        if [ $TYPE_EXIT -ne 0 ]; then
            echo "  ✗ TYPECHECK: FAIL"
            TYPE_ERRORS=$(echo "$TYPE_OUTPUT" | grep -E "error|Error" | head -10)
        else
            echo "  ✓ TYPECHECK: PASS"
            TYPE_ERRORS=""
        fi

        LAST_ERRORS=$(cat <<EOF
LINT ERRORS:
$LINT_ERRORS

TYPECHECK ERRORS:
$TYPE_ERRORS
EOF
)
        echo ""
        echo "  Errors to fix:"
        echo "$LAST_ERRORS" | head -20
    fi

    # Cleanup task from scheduler
    curl -s -X DELETE http://127.0.0.1:5679/api/tasks/$TASK_ID > /dev/null
done
```

### Finalization

```bash
if [ "$SUCCESS" = "true" ]; then
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "  SUCCESS after $ATTEMPT attempts!"
    echo "═══════════════════════════════════════════════════════════"
    echo ""

    # Copy to final destination
    mkdir -p $(dirname $ARGUMENTS.output_path)
    cp -r $RETRY_DIR/attempt_$ATTEMPT/* $(dirname $ARGUMENTS.output_path)/

    echo "  Output copied to: $ARGUMENTS.output_path"

    # Cleanup
    rm -rf $RETRY_DIR

    echo "  Cleanup: complete"
    echo ""
    echo "  Next steps:"
    echo "    1. Review the generated code"
    echo "    2. Run full test suite: make test"
    echo "    3. Commit changes"

else
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "  FAILED after $MAX_ATTEMPTS attempts"
    echo "═══════════════════════════════════════════════════════════"
    echo ""

    echo "  Last errors:"
    echo "$LAST_ERRORS"
    echo ""

    echo "  Suggestions:"
    echo "    1. Simplify the task into smaller parts"
    echo "    2. Add more context files to the prompt"
    echo "    3. Try /parallel-workers for diverse approaches"
    echo "    4. Review CLAUDE.md conventions"
    echo ""

    echo "  Retry artifacts preserved in: $RETRY_DIR"
    echo "  You can inspect each attempt and manually fix issues."
fi
```

## Example Usage

```bash
# Simple file generation
/retry-until-green "Create cli_jobs.py with list, get, create, delete commands for the jobs API. Follow cli_tasks.py pattern." --output_path claude_code_scheduler/cli_jobs.py

# With more context
/retry-until-green "Create a new JobsPanel widget for the GUI. Reference TaskListPanel for structure. Include: job list view, add/delete buttons, selection handling." --output_path claude_code_scheduler/ui/panels/jobs_panel.py --max_attempts 7
```

## Error Recovery

If all attempts fail, the retry directory is preserved:

```
./retry_1234567890/
├── attempt_1/
│   └── cli_jobs.py      # Has lint errors
├── attempt_2/
│   └── cli_jobs.py      # Has type errors
└── attempt_3/
    └── cli_jobs.py      # Almost working
```

You can:
1. Inspect each attempt to understand the issues
2. Manually fix the best attempt
3. Use as reference for a new prompt
