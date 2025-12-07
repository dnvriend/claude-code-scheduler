---
description: Execute job.json with parallel redundant workers
arguments:
  - name: job_file
    description: Path to job definition (default: ./job.json)
    default: "./job.json"
---

# Orchestrator

You are a **Sonnet Orchestrator Agent** responsible for executing jobs with parallel redundant workers.

## Your Role

1. **Read** the job definition
2. **Create** candidate directory structure
3. **Dispatch** workers via scheduler API
4. **Monitor** completion
5. **Trigger** QC for each task
6. **Finalize** winners

## Input

Job file: $ARGUMENTS.job_file

## Configuration

```
SCHEDULER_API: http://127.0.0.1:5679
ZAI_PROFILE_ID: 5270805b-3731-41da-8710-fe765f2e58be
DEFAULT_WORKERS: 3
POLL_INTERVAL: 15 seconds
```

## Process

### Step 1: Load Job Definition

```bash
# Read job.json
cat $ARGUMENTS.job_file
```

Validate required fields:
- name, description
- phases[].tasks[]
- Each task: id, name, prompt, output_path, workers

### Step 2: Create Directory Structure

```bash
# Create candidates root
mkdir -p ./candidates

# For each phase and task, create worker directories
for phase in job.phases:
    for task in phase.tasks:
        for worker_id in 1..task.workers:
            mkdir -p ./candidates/task_${task.id}/worker_${worker_id}/
```

### Step 3: Execute Phases Sequentially

For each phase (in order of parallel_group):

#### 3a. Dispatch Workers (Parallel)

For each task in the phase, create scheduler tasks:

```bash
for task in phase.tasks:
    for worker_id in 1..task.workers:

        # Build worker prompt with output path
        WORKER_PROMPT=$(cat <<EOF
${task.prompt}

IMPORTANT OUTPUT INSTRUCTIONS:
- Write your output to: ./candidates/task_${task.id}/worker_${worker_id}/
- Follow CLAUDE.md conventions
- Include docstrings and type hints
- Make it pass: ${task.success_criteria}

CONTEXT FILES TO REFERENCE:
${task.context_files}
EOF
)

        # Create task via API (uses 'prompt' field)
        TASK_RESPONSE=$(curl -s -X POST http://127.0.0.1:5679/api/tasks \
            -H "Content-Type: application/json" \
            -d '{
                "name": "worker-${task.id}-${worker_id}-$(date +%s)",
                "prompt": "'"${WORKER_PROMPT}"'",
                "model": "sonnet",
                "profile": "5270805b-3731-41da-8710-fe765f2e58be",
                "permissions": "bypass",
                "schedule": {"schedule_type": "manual"},
                "enabled": false
            }')

        TASK_ID=$(echo $TASK_RESPONSE | jq -r '.task.id')

        # Run immediately
        curl -s -X POST http://127.0.0.1:5679/api/tasks/${TASK_ID}/run

        # Store for tracking
        echo "${TASK_ID}" >> ./candidates/task_${task.id}/worker_ids.txt
```

#### 3b. Poll for Completion

```bash
while true:
    # Check all runs for this phase
    RUNS=$(curl -s http://127.0.0.1:5679/api/runs)

    # Count completed vs total
    COMPLETED=$(echo $RUNS | jq '[.runs[] | select(.task_name | startswith("worker-")) | select(.status == "success" or .status == "failed")] | length')
    TOTAL=$(cat ./candidates/task_*/worker_ids.txt | wc -l)

    echo "Progress: ${COMPLETED}/${TOTAL} workers complete"

    if [ $COMPLETED -eq $TOTAL ]; then
        break
    fi

    sleep 15
```

#### 3c. Run QC for Each Task

```bash
for task in phase.tasks:
    echo "=== QC for Task ${task.id}: ${task.name} ==="

    # Use /qc command logic inline
    BEST_SCORE=0
    BEST_WORKER=""

    for worker_dir in ./candidates/task_${task.id}/worker_*/:
        WORKER_ID=$(basename $worker_dir)

        # Run QC checks
        cd $worker_dir

        LINT_PASS=false
        if make lint 2>&1 > /dev/null; then
            LINT_PASS=true
        fi

        TYPECHECK_PASS=false
        if make typecheck 2>&1 > /dev/null; then
            TYPECHECK_PASS=true
        fi

        LOC=$(find . -name "*.py" -exec wc -l {} + | tail -1 | awk '{print $1}')

        # Calculate score
        SCORE=0
        if [ "$LINT_PASS" = true ]; then SCORE=$((SCORE + 5)); fi
        if [ "$TYPECHECK_PASS" = true ]; then SCORE=$((SCORE + 5)); fi
        if [ $LOC -gt 0 ] && [ $LOC -lt 500 ]; then SCORE=$((SCORE + 3)); fi

        echo "  ${WORKER_ID}: lint=${LINT_PASS} type=${TYPECHECK_PASS} loc=${LOC} score=${SCORE}"

        if [ $SCORE -gt $BEST_SCORE ]; then
            BEST_SCORE=$SCORE
            BEST_WORKER=$worker_dir
        fi

        cd -
    done

    if [ -z "$BEST_WORKER" ]; then
        echo "ERROR: No candidates passed QC for task ${task.id}"
        echo "Consider: /retry-until-green with the task prompt"
        continue
    fi

    echo "  WINNER: ${BEST_WORKER} (score: ${BEST_SCORE})"

    # Move winner to final location
    cp -r ${BEST_WORKER}/* $(dirname ${task.output_path})/
    echo "  Copied to: ${task.output_path}"
```

### Step 4: Cleanup

```bash
# Remove candidates directory
rm -rf ./candidates/

# Delete temporary scheduler tasks
for task_id in $(cat ./candidates/task_*/worker_ids.txt 2>/dev/null):
    curl -s -X DELETE http://127.0.0.1:5679/api/tasks/${task_id}

# Update job status
jq '.status = "completed"' job.json > job.json.tmp && mv job.json.tmp job.json
```

### Step 5: Report

```
## Orchestration Complete

### Results by Phase

Phase 1: [name]
  - Task 1.1: worker_3 selected (score: 13/15)
  - Task 1.2: worker_1 selected (score: 15/15)

Phase 2: [name]
  - Task 2.1: worker_2 selected (score: 12/15)

### Summary
- Tasks completed: X/Y
- Total workers run: Z
- Winners selected: X
- Cleanup: complete

### Next Steps
1. Run `make lint && make typecheck` to verify
2. Review generated code
3. Commit changes
```

## Error Handling

### Worker Timeout
If a worker doesn't complete within 10 minutes:
```bash
curl -X POST http://127.0.0.1:5679/api/runs/${RUN_ID}/stop
```

### All Candidates Fail
If no candidate passes QC:
1. Log the errors
2. Suggest `/retry-until-green` with refined prompt
3. Continue to next task (don't block)

### API Unavailable
```bash
if ! curl -s http://127.0.0.1:5679/api/health > /dev/null; then
    echo "ERROR: Scheduler API not available at http://127.0.0.1:5679"
    echo "Start the GUI: claude-code-scheduler gui"
    exit 1
fi
```
