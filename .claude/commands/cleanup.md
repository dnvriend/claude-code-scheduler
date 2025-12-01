---
description: Remove all candidates, temporary tasks, and reset orchestration state
---

# Cleanup

Remove all temporary files and tasks from a failed or abandoned orchestration run.

## Process

### Step 1: Remove Candidates Directory

```bash
echo "Cleaning up candidates..."

if [ -d "./candidates" ]; then
    # Count what we're removing
    TASK_DIRS=$(ls -d ./candidates/task_*/ 2>/dev/null | wc -l | tr -d ' ')
    WORKER_DIRS=$(ls -d ./candidates/task_*/worker_*/ 2>/dev/null | wc -l | tr -d ' ')

    rm -rf ./candidates
    echo "  Removed: ./candidates/"
    echo "  Tasks: $TASK_DIRS"
    echo "  Workers: $WORKER_DIRS"
else
    echo "  No candidates directory found"
fi
```

### Step 2: Remove Retry Directories

```bash
echo ""
echo "Cleaning up retry directories..."

RETRY_DIRS=$(ls -d ./retry_* 2>/dev/null)
if [ -n "$RETRY_DIRS" ]; then
    for DIR in $RETRY_DIRS; do
        rm -rf "$DIR"
        echo "  Removed: $DIR"
    done
else
    echo "  No retry directories found"
fi
```

### Step 3: Remove Job Definition

```bash
echo ""
echo "Cleaning up job.json..."

if [ -f "./job.json" ]; then
    # Archive instead of delete (in case needed)
    mv ./job.json ./job.json.bak.$(date +%s)
    echo "  Archived: job.json → job.json.bak.*"
else
    echo "  No job.json found"
fi
```

### Step 4: Remove Temporary Scheduler Tasks

```bash
echo ""
echo "Cleaning up scheduler tasks..."

# Check API availability
if ! curl -s http://127.0.0.1:5679/api/health > /dev/null 2>&1; then
    echo "  WARNING: Scheduler API not available"
    echo "  Temporary tasks may remain - clean up manually when GUI is running"
else
    # Find and delete temporary tasks
    TEMP_TASKS=$(curl -s http://127.0.0.1:5679/api/tasks | \
        jq -r '.tasks[] | select(.name | test("^worker-|^retry-attempt-|^parallel-worker-")) | .id')

    if [ -n "$TEMP_TASKS" ]; then
        for TASK_ID in $TEMP_TASKS; do
            curl -s -X DELETE http://127.0.0.1:5679/api/tasks/$TASK_ID > /dev/null
            echo "  Deleted task: $TASK_ID"
        done
        DELETED=$(echo "$TEMP_TASKS" | wc -l | tr -d ' ')
        echo "  Total deleted: $DELETED tasks"
    else
        echo "  No temporary tasks found"
    fi
fi
```

### Step 5: Remove QC Artifacts

```bash
echo ""
echo "Cleaning up QC artifacts..."

rm -f ./qc_results.json 2>/dev/null && echo "  Removed: qc_results.json" || echo "  No qc_results.json found"
rm -f /tmp/lint_output.txt 2>/dev/null
rm -f /tmp/type_output.txt 2>/dev/null
rm -f /tmp/test_output.txt 2>/dev/null
```

### Summary

```
═══════════════════════════════════════════════════════════════════════
  CLEANUP COMPLETE
═══════════════════════════════════════════════════════════════════════

  Removed:
    • candidates/ directory
    • retry_* directories
    • job.json (archived)
    • Temporary scheduler tasks
    • QC artifacts

  Workspace is clean and ready for new orchestration.

  To start fresh:
    /plan "Your feature description"
```
