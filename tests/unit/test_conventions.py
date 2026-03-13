"""Convention tests for Sahayakan.

These tests enforce project-specific coding conventions by inspecting source files.
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

# Patterns that suggest hardcoded credentials
CREDENTIAL_PATTERNS = [
    r"""(?:password|passwd|secret|api_key|apikey|token)\s*=\s*["'][^"']{8,}["']""",
    r"""(?:password|passwd|secret|api_key|apikey|token)\s*:\s*["'][^"']{8,}["']""",
]

# Known exceptions (test files, env defaults)
CREDENTIAL_EXCEPTIONS = [
    "test_",
    "example",
    ".env",
    "sahayakan_dev_password",  # documented dev default
]


def _get_python_files(*dirs):
    """Recursively find all .py files in the given directories."""
    files = []
    for d in dirs:
        if not os.path.exists(d):
            continue
        for root, _, filenames in os.walk(d):
            for f in filenames:
                if f.endswith(".py"):
                    files.append(os.path.join(root, f))
    return files


def test_route_files_export_router():
    """Each route module must define router = APIRouter(...)."""
    for route_file in os.listdir(ROUTES_DIR):
        if not route_file.endswith(".py") or route_file == "__init__.py":
            continue

        filepath = os.path.join(ROUTES_DIR, route_file)
        with open(filepath) as f:
            content = f.read()

        assert re.search(r"router\s*=\s*APIRouter\(", content), (
            f"Route file {route_file} does not define router = APIRouter(...)"
        )


def test_agent_init_signature():
    """Agent __init__ must accept knowledge_cache and logger parameters."""
    agent_dirs = [
        d for d in os.listdir(AGENTS_DIR) if os.path.isdir(os.path.join(AGENTS_DIR, d)) and not d.startswith("__")
    ]

    for agent_dir in agent_dirs:
        agent_file = os.path.join(AGENTS_DIR, agent_dir, "agent.py")
        with open(agent_file) as f:
            content = f.read()

        tree = ast.parse(content)
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            for item in node.body:
                if not (isinstance(item, ast.FunctionDef) and item.name == "__init__"):
                    continue
                arg_names = [a.arg for a in item.args.args]
                assert "knowledge_cache" in arg_names, f"Agent {agent_dir} __init__ missing 'knowledge_cache' parameter"
                assert "logger" in arg_names, f"Agent {agent_dir} __init__ missing 'logger' parameter"


def test_no_hardcoded_credentials():
    """No hardcoded credentials in production source files."""
    source_dirs = [
        os.path.join(CONTROL_PLANE),
        os.path.join(DATA_PLANE, "agent_runner"),
        os.path.join(DATA_PLANE, "agents"),
        os.path.join(DATA_PLANE, "llm_client"),
    ]

    for py_file in _get_python_files(*source_dirs):
        basename = os.path.basename(py_file)

        # Skip known exception files
        if any(exc in basename or exc in py_file for exc in CREDENTIAL_EXCEPTIONS):
            continue

        with open(py_file) as f:
            content = f.read()

        for pattern in CREDENTIAL_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                # Allow os.environ.get() defaults with known dev passwords
                if any(exc in match for exc in CREDENTIAL_EXCEPTIONS):
                    continue
                raise AssertionError(f"Possible hardcoded credential in {py_file}: {match}")


def test_prompt_templates_use_placeholder_syntax():
    """Prompt templates should use {placeholder} syntax, not f-strings or % formatting."""
    for prompt_file in os.listdir(PROMPTS_DIR):
        if not prompt_file.endswith(".prompt"):
            continue

        filepath = os.path.join(PROMPTS_DIR, prompt_file)
        with open(filepath) as f:
            content = f.read()

        # Check for Python f-string markers (shouldn't be in .prompt files)
        assert not re.search(r"f['\"]", content), (
            f"Prompt {prompt_file} contains f-string syntax. Use {{placeholder}} instead"
        )

        # Check for % formatting
        assert not re.search(r"%\([a-z_]+\)s", content), (
            f"Prompt {prompt_file} contains %-formatting. Use {{placeholder}} instead"
        )


if __name__ == "__main__":
    test_route_files_export_router()
    print("  PASS: All route files export router")

    test_agent_init_signature()
    print("  PASS: All agent __init__ signatures correct")

    test_no_hardcoded_credentials()
    print("  PASS: No hardcoded credentials found")

    test_prompt_templates_use_placeholder_syntax()
    print("  PASS: Prompt templates use correct syntax")

    print("\nAll convention tests passed!")
