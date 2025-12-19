# RAW Test Scenarios

End-to-end test scenarios for RAW runtime features.

1. The "Standard" Data Pipeline
Goal: Test basic scaffolding, tool creation/reuse, and reporting.
Fetch the current price of Bitcoin and Ethereum from CoinGecko, compare them to their 7-day moving averages, and generate a markdown report highlighting if they are in a 'Buy' or 'Sell' zone based on simple trend logic."

2. The "Human-in-the-Loop" Check (Connected Mode)
Goal: Test raw serve, the Dashboard, and the wait_for_approval logic.
Check the status of the production website (e.g., google.com) to see if it returns 200 OK. If it does, pause and ask for Human Approval to 'Proceed with imaginary deployment'. If approved, write a 'DEPLOY_SUCCESS' file. If rejected, write 'DEPLOY_CANCELLED'."

3. The "External Trigger" (Webhook)
Goal: Test wait_for_webhook and the ability to resume workflows from an external signal.
Start a workflow that generates a unique ID, prints it, and then waits for a webhook payload containing a 'user_email'. Once received, parse the email domain and save it to a file named 'domain.txt'."

4. The "Resiliency" Test (Retries & Errors)
Goal: Test @retry logic and error handling. (You might need to manually modify the URL in the generated code to be invalid to force retries).
Attempt to fetch data from 'https://httpstat.us/503' (simulating a flaky API). Use retry logic with exponential backoff to try at least 5 times before failing. If it eventually fails, catch the error and save a 'failure_log.txt' artifact instead of crashing."

5. The "Complex Research" Agent
Goal: Test multiple tools and complex logic flow.
Search HackerNews for the top 5 stories about 'AI Agents'. For each story, fetch the linked article content (if possible) and summarize it in 2 sentence Compile a final JSON digest of title, link, and summary."

---

## Scenario 1: Retry with Exponential Backoff
**Query**: "Test that steps can retry automatically with exponential backoff"
**Workflow**: `retry_test`
**Expected Steps**: `unreliable_fetch`
**Expected Tools**: None (pure runtime feature)
**Expected Behavior**:
- Step fails 2 times by default
- Retry decorator catches failures and retries up to 3 times
- Exponential backoff between retries (1s, 2s, 4s)
- Succeeds on attempt 3
**Verification**: `results.json` shows `succeeded: true` and `total_attempts: 3`

---

## Scenario 2: Step Caching
**Query**: "Test that expensive steps are cached and not re-executed"
**Workflow**: `cache_test`
**Expected Steps**: `expensive_compute`
**Expected Tools**: None (pure runtime feature)
**Expected Behavior**:
- First call computes (1 second delay)
- Second call with same input returns cached result (instant)
- Third call with different input computes again
**Verification**: `results.json` shows `total_computes: 2` and `cache_worked: true`

---

## Scenario 3: Conditional Step Execution
**Query**: "Test that steps can be conditionally skipped based on runtime conditions"
**Workflow**: `conditional_test`
**Expected Steps**: `check_situation`, `send_alert`, `generate_report`
**Expected Tools**: None (pure runtime feature)
**Expected Behavior**:
- `check_situation` always runs
- `send_alert` only runs if `critical=True`
- `generate_report` only runs if `score > 75`
**Test Cases**:
1. `--critical --score 80`: All 3 steps run
2. No flags (defaults): Only `check_situation` runs, others skipped
**Verification**: `results.json` shows which steps ran/skipped

---

## Scenario 4: Approval Timeout
**Query**: "Test that approval requests timeout correctly"
**Workflow**: `timeout_test`
**Expected Steps**: `request_approval`
**Expected Tools**: None (pure runtime feature)
**Expected Interactions**: Approval request via server
**Expected Behavior**:
- Workflow requests approval with 5 second timeout
- If not approved within timeout, TimeoutError is caught
- Workflow returns "timeout" result
**Verification**: `results.json` shows `timed_out: true` when no approval given

---

## Scenario 5: Webhook Data Delivery
**Query**: "Test that workflows can wait for and receive webhook data"
**Workflow**: `webhook_test`
**Expected Steps**: `wait_for_data`, `process`
**Expected Tools**: None (pure runtime feature)
**Expected Interactions**:
- POST to `/send/{run_id}/{step_name}` with payload
**Expected Behavior**:
- Workflow starts and waits for webhook data
- External system sends data via `/send` endpoint
- Workflow receives data and continues processing
**Verification**: `results.json` contains the webhook payload data

---

## Scenario 6: Human Approval Flow
**Query**: "Test that workflows can pause for human approval"
**Workflow**: `approval_test`
**Expected Steps**: `fetch_data`, `process_data`
**Expected Tools**: None (pure runtime feature)
**Expected Interactions**:
- GET `/approvals` to see pending approvals
- POST `/approve/{run_id}/{step_name}?decision=approve`
**Expected Behavior**:
- Workflow pauses at approval step
- Shows in `/approvals` list
- Resumes when human approves/rejects
**Verification**: Workflow completes after approval with decision recorded

---

## Running Tests

### Start the server
```bash
raw serve -p 8765
```

### Trigger workflow via webhook
```bash
curl -X POST http://localhost:8765/webhook/{workflow_id} \
  -H "Content-Type: application/json" \
  -d '{"args": ["--flag", "value"]}'
```

### Check pending approvals
```bash
curl http://localhost:8765/approvals
```

### Approve a step
```bash
curl -X POST "http://localhost:8765/approve/{run_id}/{step_name}?decision=approve"
```

### Send webhook data
```bash
curl -X POST http://localhost:8765/send/{run_id}/{step_name} \
  -H "Content-Type: application/json" \
  -d '{"key": "value"}'
```

### Run directly (without server)
```bash
raw run {workflow_id} --arg value
```
