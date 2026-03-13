Scaffold a new Sahayakan agent named "$ARGUMENTS".

Follow these steps:

1. Convert the agent name to snake_case for directory names (e.g., "my-agent" -> "my_agent") and to a class name in PascalCase (e.g., "MyAgentAgent").

2. Create `data-plane/agents/{snake_name}/__init__.py` (empty file).

3. Create `data-plane/agents/{snake_name}/agent.py` with a BaseAgent subclass following the pattern in `data-plane/agents/dummy/agent.py`:
   - Import `AgentInput`, `AgentOutput`, `BaseAgent` from `agent_runner.contracts.base_agent`
   - Import `KnowledgeCache` from `agent_runner.knowledge`
   - Import `AgentLogger` from `agent_runner.logging_utils`
   - `__init__` accepts `knowledge_cache` and `logger` (and optionally `llm_client`)
   - Implement all 5 methods: `load_input`, `collect_context`, `analyze`, `generate_output`, `store_artifacts`

4. Create `data-plane/prompts/{name}.prompt` with a basic prompt template using `{placeholder}` syntax.

5. Update `data-plane/agent_runner/main.py`:
   - Add an import for the new agent class
   - Add a registry entry using hyphenated name as key (e.g., "my-agent": MyAgentAgent)

6. Update `tests/unit/test_agent_contract.py`:
   - Add an import for the new agent class
   - Add the class to both test lists (`test_all_agents_are_base_agent` and `test_all_agents_implement_methods`)

7. Report what was created and what the user should do next.
