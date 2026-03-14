# Jobs Page

The Jobs page shows all agent execution jobs — running, completed, failed, and those awaiting review.

## Job List

Each job row shows:

- **ID** — Unique job identifier
- **Agent** — Which agent is running
- **Status** — `pending`, `running`, `completed`, `failed`, or `awaiting_review`
- **Created** — When the job was submitted
- **Duration** — How long the job took (for completed jobs)

## Job Details

Click a job to see:

- **Parameters** — Input parameters passed to the agent
- **Logs** — Real-time streaming logs via WebSocket
- **Artifacts** — Links to generated reports and outputs
- **LLM Usage** — Token counts and estimated cost

## Reviewing Jobs

When a job is paused at a review gate:

1. The status shows `awaiting_review`
2. Click the job to see what stage it paused at
3. Review the intermediate output
4. Click **Approve** to continue or **Reject** with a reason

You can also review jobs via the CLI:

```bash
# Approve a job
python3 -m cli.main job review 42 --approve

# Reject with reason
python3 -m cli.main job review 42 --reject "Analysis looks incorrect"
```
