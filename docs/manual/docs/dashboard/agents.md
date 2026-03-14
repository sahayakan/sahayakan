# Agents Page

The Agents page shows all registered agents and lets you run them or configure review gates.

## Agent List

Each agent card displays:

- **Name** — The agent identifier (e.g., `issue-triage`)
- **Version** — Current version
- **Description** — What the agent does
- **Status** — Whether it's idle or running a job

## Running an Agent

1. Click the **Run** button on an agent card
2. Fill in the required parameters (e.g., issue number, PR number)
3. Click **Submit** to create a new job

The job will appear on the [Jobs page](jobs.md) where you can monitor its progress.

## Review Gates

Review gates let you pause agent execution at specific stages for human review. To configure:

1. Click the **Gates** icon on an agent card
2. Toggle individual stages on or off:
   - **load_input** — After input validation
   - **collect_context** — After context gathering
   - **analyze** — After LLM analysis
   - **generate_output** — After report generation

When a gate is active, the job pauses with status `awaiting_review`. You can approve or reject it from the Jobs page or via the CLI.
