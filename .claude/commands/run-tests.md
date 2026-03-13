Run Sahayakan tests. Argument: "$ARGUMENTS"

Based on the argument, run the appropriate tests:

- If "unit": Run all files matching `tests/unit/test_*.py` by executing each with `python {file}`.
- If "e2e": Run all files matching `tests/test_*_e2e.py` by executing each with `python {file}`. Note: these require a running database (podman-compose up).
- If "all": Run both unit and e2e tests.
- If a specific filename is given (e.g., "test_agent_contract.py"): Find and run that specific test file.
- If empty/blank: Default to "unit".

For each test file, run it from the project root directory. Report pass/fail results for each file. If a test fails, show the error output.
