"""Structural boundary tests for Sahayakan.

These tests verify architectural invariants without importing application code.
They inspect the file system and source code directly.
"""

import ast
import os
import re

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_PLANE = os.path.join(PROJECT_ROOT, "data-plane")
CONTROL_PLANE = os.path.join(PROJECT_ROOT, "control-plane", "api-server", "app")
AGENTS_DIR = os.path.join(DATA_PLANE, "agents")
PROMPTS_DIR = os.path.join(DATA_PLANE, "prompts")
ROUTES_DIR = os.path.join(CONTROL_PLANE, "routes")
MIGRATIONS_DIR = os.path.join(PROJECT_ROOT, "infrastructure", "db", "migrations")
REGISTRY_FILE = os.path.join(DATA_PLANE, "agent_runner", "main.py")
MAIN_FILE = os.path.join(CONTROL_PLANE, "main.py")


def _get_agent_dirs():
    """Return list of agent directory names (excluding __pycache__)."""
    return [d for d in os.listdir(AGENTS_DIR) if os.path.isdir(os.path.join(AGENTS_DIR, d)) and not d.startswith("__")]


def _get_registry_keys():
    """Parse get_agent_registry() and return the set of registered keys."""
    with open(REGISTRY_FILE) as f:
        content = f.read()
    # Match string keys in the registry dict
    return set(re.findall(r'"([a-z][a-z0-9-]*)"(?=\s*:)', content))


def _get_route_modules():
    """Return list of route module names (excluding __init__)."""
    return [f[:-3] for f in os.listdir(ROUTES_DIR) if f.endswith(".py") and f != "__init__.py"]


def _get_registered_routes():
    """Parse main.py and return set of module names included via include_router."""
    with open(MAIN_FILE) as f:
        content = f.read()
    return set(re.findall(r"include_router\((\w+)\.router\)", content))


def test_all_agents_inherit_base_agent():
    """All agent.py files must contain a class inheriting from BaseAgent."""
    for agent_dir in _get_agent_dirs():
        agent_file = os.path.join(AGENTS_DIR, agent_dir, "agent.py")
        assert os.path.exists(agent_file), f"Missing agent.py in {agent_dir}"

        with open(agent_file) as f:
            content = f.read()

        tree = ast.parse(content)
        classes = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef)
            and any(
                (isinstance(base, ast.Name) and base.id == "BaseAgent")
                or (isinstance(base, ast.Attribute) and base.attr == "BaseAgent")
                for base in node.bases
            )
        ]
        assert classes, f"No class inheriting BaseAgent found in agents/{agent_dir}/agent.py"


def test_all_agents_registered():
    """Every agent directory must have a corresponding registry entry."""
    agent_dirs = _get_agent_dirs()
    registry_keys = _get_registry_keys()

    # Convert dir names (underscores) to registry format (hyphens)
    for agent_dir in agent_dirs:
        expected_key = agent_dir.replace("_", "-")
        assert expected_key in registry_keys, (
            f"Agent '{agent_dir}' not registered in get_agent_registry(). Expected key '{expected_key}'"
        )


def test_all_agents_have_prompt_templates():
    """Each agent directory should have a corresponding .prompt file."""
    prompt_files = [f[:-7] for f in os.listdir(PROMPTS_DIR) if f.endswith(".prompt")]
    agent_dirs = _get_agent_dirs()

    # Dummy agent is exempt (no LLM calls)
    agent_dirs = [d for d in agent_dirs if d != "dummy"]

    for agent_dir in agent_dirs:
        # Check for any prompt file that could belong to this agent
        # Prompt names may differ slightly (e.g., issue_triage -> issue_analysis)
        matching = [p for p in prompt_files if any(part in p for part in agent_dir.split("_"))]
        assert matching, f"No prompt template found for agent '{agent_dir}'. Available prompts: {prompt_files}"


def test_all_routes_registered():
    """All route modules must be registered in main.py via include_router."""
    route_modules = set(_get_route_modules())
    registered = _get_registered_routes()

    unregistered = route_modules - registered
    assert not unregistered, (
        f"Route modules not registered in main.py: {unregistered}. Add app.include_router(<module>.router) to main.py"
    )


def test_migration_numbering():
    """Migration files must be sequentially numbered with no gaps or duplicates."""
    files = sorted(f for f in os.listdir(MIGRATIONS_DIR) if f.endswith(".sql"))
    assert files, "No migration files found"

    numbers = []
    for f in files:
        match = re.match(r"^(\d+)_", f)
        assert match, f"Migration file '{f}' doesn't follow NNN_name.sql pattern"
        numbers.append(int(match.group(1)))

    # Check for duplicates
    assert len(numbers) == len(set(numbers)), f"Duplicate migration numbers found: {numbers}"

    # Check sequential (starting from 1)
    expected = list(range(1, len(numbers) + 1))
    assert numbers == expected, f"Migration numbers not sequential. Got {numbers}, expected {expected}"


def test_registry_naming_convention():
    """Registry keys use hyphens, directory names use underscores."""
    registry_keys = _get_registry_keys()
    agent_dirs = _get_agent_dirs()

    for key in registry_keys:
        assert "_" not in key, f"Registry key '{key}' uses underscores; should use hyphens"

    for d in agent_dirs:
        assert "-" not in d, f"Agent directory '{d}' uses hyphens; should use underscores"


def test_no_cross_boundary_imports():
    """Agents must not import from control-plane; routes must not import from data-plane."""
    # Check agents don't import from control-plane
    for agent_dir in _get_agent_dirs():
        agent_file = os.path.join(AGENTS_DIR, agent_dir, "agent.py")
        with open(agent_file) as f:
            content = f.read()
        assert "control-plane" not in content and "control_plane" not in content, (
            f"Agent {agent_dir} imports from control-plane (cross-boundary violation)"
        )

    # Check routes don't import from data-plane
    for route_file in os.listdir(ROUTES_DIR):
        if not route_file.endswith(".py") or route_file == "__init__.py":
            continue
        filepath = os.path.join(ROUTES_DIR, route_file)
        with open(filepath) as f:
            content = f.read()
        # Allow "data-plane" in comments/strings but not in import statements
        for line in content.split("\n"):
            if line.strip().startswith("#"):
                continue
            if re.match(r"^\s*(from|import)\s+.*data.plane", line):
                raise AssertionError(f"Route {route_file} imports from data-plane (cross-boundary violation): {line}")


if __name__ == "__main__":
    test_all_agents_inherit_base_agent()
    print("  PASS: All agents inherit BaseAgent")

    test_all_agents_registered()
    print("  PASS: All agents registered in registry")

    test_all_agents_have_prompt_templates()
    print("  PASS: All agents have prompt templates")

    test_all_routes_registered()
    print("  PASS: All routes registered in main.py")

    test_migration_numbering()
    print("  PASS: Migration numbering is sequential")

    test_registry_naming_convention()
    print("  PASS: Registry naming conventions correct")

    test_no_cross_boundary_imports()
    print("  PASS: No cross-boundary imports")

    print("\nAll structural tests passed!")
