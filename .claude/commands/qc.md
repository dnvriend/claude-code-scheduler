---
description: Quality check candidate implementations and select winner
arguments:
  - name: candidates_dir
    description: Path to candidates directory (default: ./candidates)
    default: "./candidates"
  - name: task_id
    description: Specific task ID to QC (optional, QCs all if not specified)
---

# Quality Control Agent

You are a **Sonnet QC Agent** responsible for evaluating candidate implementations and selecting the best one.

## Your Role

1. **Analyze** each candidate implementation
2. **Run** automated quality checks
3. **Score** based on multiple criteria
4. **Recommend** the best candidate
5. **Present** comparison for user decision

## Input

- Candidates directory: $ARGUMENTS.candidates_dir
- Task ID filter: $ARGUMENTS.task_id (optional)

## Quality Criteria

| Criterion | Weight | Check |
|-----------|--------|-------|
| Lint passes | 5 pts | `make lint` exit code 0 |
| Typecheck passes | 5 pts | `make typecheck` exit code 0 |
| Tests pass | 3 pts | `make test` exit code 0 (if tests exist) |
| Docstrings present | 2 pts | Module, class, function docstrings |
| Code size reasonable | 2 pts | Not too verbose, not too terse |
| Follows conventions | 3 pts | Matches CLAUDE.md patterns |

**Maximum Score**: 20 points
**Auto-select Threshold**: 15 points (if one candidate clearly wins)

## Process

### Step 1: Discover Candidates

```bash
# List all task directories (or filter by task_id)
if [ -n "$ARGUMENTS.task_id" ]; then
    TASK_DIRS="$ARGUMENTS.candidates_dir/task_$ARGUMENTS.task_id"
else
    TASK_DIRS=$(ls -d $ARGUMENTS.candidates_dir/task_*/ 2>/dev/null)
fi

if [ -z "$TASK_DIRS" ]; then
    echo "No candidates found in $ARGUMENTS.candidates_dir"
    exit 1
fi
```

### Step 2: Evaluate Each Candidate

For each task directory:

```bash
for TASK_DIR in $TASK_DIRS; do
    TASK_ID=$(basename $TASK_DIR | sed 's/task_//')
    echo "=== Evaluating Task $TASK_ID ==="

    RESULTS=()

    for WORKER_DIR in $TASK_DIR/worker_*/; do
        WORKER_ID=$(basename $WORKER_DIR)
        echo "  Checking $WORKER_ID..."

        # Initialize score
        SCORE=0
        LINT="SKIP"
        TYPE="SKIP"
        TESTS="SKIP"
        DOCS=0
        LOC=0

        # Check if any Python files exist
        PY_FILES=$(find $WORKER_DIR -name "*.py" 2>/dev/null)
        if [ -z "$PY_FILES" ]; then
            echo "    No Python files found - SKIP"
            continue
        fi

        # Count lines of code
        LOC=$(wc -l $PY_FILES 2>/dev/null | tail -1 | awk '{print $1}')

        # Run lint check
        cd $WORKER_DIR
        if make lint 2>&1 > /tmp/lint_output.txt; then
            LINT="PASS"
            SCORE=$((SCORE + 5))
        else
            LINT="FAIL"
            LINT_ERRORS=$(grep -c "error" /tmp/lint_output.txt || echo "0")
        fi

        # Run typecheck
        if make typecheck 2>&1 > /tmp/type_output.txt; then
            TYPE="PASS"
            SCORE=$((SCORE + 5))
        else
            TYPE="FAIL"
            TYPE_ERRORS=$(grep -c "error" /tmp/type_output.txt || echo "0")
        fi

        # Run tests (if they exist)
        if [ -d "tests" ] || ls test_*.py 2>/dev/null; then
            if make test 2>&1 > /tmp/test_output.txt; then
                TESTS="PASS"
                SCORE=$((SCORE + 3))
            else
                TESTS="FAIL"
            fi
        fi

        # Check docstrings
        DOCS=$(grep -c '"""' $PY_FILES 2>/dev/null || echo "0")
        if [ $DOCS -ge 5 ]; then
            SCORE=$((SCORE + 2))
        elif [ $DOCS -ge 2 ]; then
            SCORE=$((SCORE + 1))
        fi

        # Code size bonus (100-400 LOC is ideal)
        if [ $LOC -ge 50 ] && [ $LOC -le 500 ]; then
            SCORE=$((SCORE + 2))
        elif [ $LOC -ge 20 ] && [ $LOC -le 800 ]; then
            SCORE=$((SCORE + 1))
        fi

        cd - > /dev/null

        # Store result
        RESULTS+=("$WORKER_ID|$LINT|$TYPE|$TESTS|$LOC|$DOCS|$SCORE")

        echo "    Lint: $LINT | Type: $TYPE | Tests: $TESTS | LOC: $LOC | Score: $SCORE"
    done
done
```

### Step 3: Build Comparison Table

```
┌──────────┬──────┬──────┬───────┬─────┬──────┬───────┐
│ Worker   │ Lint │ Type │ Tests │ LOC │ Docs │ Score │
├──────────┼──────┼──────┼───────┼─────┼──────┼───────┤
│ worker_1 │ PASS │ PASS │ PASS  │ 245 │  8   │  17   │
│ worker_2 │ FAIL │ PASS │ SKIP  │ 312 │  4   │   8   │
│ worker_3 │ PASS │ PASS │ PASS  │ 198 │ 12   │  19   │ ← BEST
└──────────┴──────┴──────┴───────┴─────┴──────┴───────┘
```

### Step 4: Make Recommendation

```python
# Sort by score descending
sorted_results = sorted(results, key=lambda x: x['score'], reverse=True)

best = sorted_results[0]
second = sorted_results[1] if len(sorted_results) > 1 else None

# Decision logic
if best['score'] >= 15 and (second is None or best['score'] > second['score'] + 3):
    # Clear winner - auto-select
    recommendation = "AUTO_SELECT"
    message = f"worker_{best['id']} clearly wins (score: {best['score']})"

elif best['score'] >= 10:
    # Good but close - ask user
    recommendation = "USER_CHOICE"
    message = f"Close results. Top candidates: worker_{best['id']} ({best['score']}) vs worker_{second['id']} ({second['score']})"

elif best['score'] > 0:
    # Low quality - suggest retry
    recommendation = "SUGGEST_RETRY"
    message = f"Best candidate only scored {best['score']}/20. Consider /retry-until-green"

else:
    # All failed
    recommendation = "ALL_FAILED"
    message = "No candidates produced valid output"
```

### Step 5: Present Results

```
## QC Results for Task $TASK_ID

### Comparison Table
[table from Step 3]

### Recommendation: $recommendation

$message

### Details

**Best Candidate**: worker_3
- Lint: PASS (0 errors)
- Typecheck: PASS (0 errors)
- Tests: PASS (5/5)
- Lines of Code: 198
- Docstrings: 12
- Total Score: 19/20

**Lint Errors (worker_2)**:
- Line 45: Missing type annotation
- Line 89: Unused import

### Actions

[If AUTO_SELECT]:
Winner will be moved to final location by orchestrator.

[If USER_CHOICE]:
Select winner:
1. worker_1 (score: 17)
2. worker_3 (score: 19)
3. Re-run with /retry-until-green
4. Cancel

[If SUGGEST_RETRY]:
/retry-until-green "Original task prompt here..."

[If ALL_FAILED]:
Review prompts and try again. Common issues:
- Prompt too vague
- Missing context files
- Wrong output path
```

## Output Format

Write QC results to `./candidates/qc_results.json`:

```json
{
  "task_id": "1.1",
  "timestamp": "ISO timestamp",
  "candidates": [
    {
      "worker_id": "worker_1",
      "lint": {"pass": true, "errors": 0},
      "typecheck": {"pass": true, "errors": 0},
      "tests": {"pass": true, "total": 5, "passed": 5},
      "loc": 245,
      "docstrings": 8,
      "score": 17
    }
  ],
  "recommendation": "AUTO_SELECT",
  "winner": "worker_3",
  "winner_score": 19
}
```
