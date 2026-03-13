Run an agent end-to-end against the test-project repo on the production server. Agent name: "$ARGUMENTS"

Supported agents: `issue-triage`, `pr-context` (and future agents as they are added).

Read `.env.local` to get SSH_KEY_PATH and AWS_SERVER_IP. Then:

1. **Determine the test script** based on agent name:
   - `issue-triage`: `tests/test_issue_triage_e2e.py`
   - `pr-context`: `tests/test_pr_context_e2e.py`
   - If unknown, check `tests/` for a matching `test_{agent_snake}_e2e.py` file.

2. **Run the test on the production server**:
   ```
   ssh -i {SSH_KEY_PATH} admin@{AWS_SERVER_IP} "cd ~/sahayakan && source .env && source .venv/bin/activate && python {test_script}"
   ```

3. **Report the results**: Show the agent output (triage labels, priority, analysis summary, etc.).

If "$ARGUMENTS" is empty, list the available agents and ask which one to test.
