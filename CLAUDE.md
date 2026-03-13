# Sahayakan - Project Conventions

## Architecture

Monorepo with four top-level components:

- **control-plane/** - FastAPI API server (`control-plane/api-server/app/`)
- **data-plane/** - Agent runtime, LLM client, agents (`data-plane/`)
- **web-ui/** - React dashboard (`web-ui/`)
- **infrastructure/** - Docker Compose, migrations, Helm (`infrastructure/`)

Supporting directories: `tests/`, `docs/`, `knowledge-cache/`, `cli/`

## Agent Conventions

All agents live in `data-plane/agents/{snake_name}/agent.py` and must:

1. Inherit from `BaseAgent` (`data-plane/agent_runner/contracts/base_agent.py`)
2. Implement all 5 lifecycle methods: `load_input`, `collect_context`, `analyze`, `generate_output`, `store_artifacts`
3. Accept `knowledge_cache: KnowledgeCache` and `logger: AgentLogger` in `__init__`
4. Have a prompt template at `data-plane/prompts/{name}.prompt`
5. Be registered in `data-plane/agent_runner/main.py` in `get_agent_registry()`

**Naming**: Registry keys use hyphens (`issue-triage`), directories use underscores (`issue_triage`).

Current agents: dummy, issue-triage, pr-context, meeting-summary, slack-digest, insights, trend-analysis

## Python Path

The data-plane uses relative imports. Scripts must add data-plane to sys.path:
```python
sys.path.insert(0, "data-plane")
```

## Database

- **Image**: `pgvector/pgvector:pg16`
- **Host port**: 5433 (maps to container 5432, avoids local Postgres conflict)
- **Credentials**: user=sahayakan, password=sahayakan_dev_password, db=sahayakan
- **Migrations**: `infrastructure/db/migrations/` numbered `001_` through `005_`
- **Next migration number**: 006

## Development Setup

```bash
# First-time setup (creates venv, installs deps, pre-commit hooks)
bash setup.sh
# Or:
make setup
```

## Common Commands (Makefile)

```bash
make lint       # ruff check + format check
make format     # auto-fix formatting and lint issues
make test       # run all unit + structural + convention tests
make test-e2e   # run E2E tests (require running DB)
make run        # start all containers
make stop       # stop all containers
make rebuild    # rebuild a service (SVC=api-server by default)
make logs       # tail logs (SVC=api-server by default)
make migrate    # apply all SQL migrations
make check      # lint + test (full pre-merge check)
```

## Container Commands

```bash
# Start all services
cd infrastructure && podman-compose --env-file ../.env up -d

# Rebuild a specific service
cd infrastructure && podman-compose --env-file ../.env up -d --build api-server

# View logs
podman-compose -f infrastructure/docker-compose.yml logs -f api-server
```

Environment variables are in `.env` at the project root.

## Testing

Tests use standalone scripts (no pytest). Run with:
```bash
# All unit tests (includes structural + convention tests)
make test

# Individual test files
python tests/unit/test_agent_contract.py
python tests/unit/test_knowledge_cache.py
python tests/unit/test_structural.py
python tests/unit/test_conventions.py

# E2E tests (require running DB)
python tests/test_issue_triage_e2e.py
```

## API Routes

Routes live in `control-plane/api-server/app/routes/`. Each module exports a `router = APIRouter(prefix="/resource", tags=["resource"])` and is registered in `control-plane/api-server/app/main.py` via `app.include_router()`.

## CLI

The CLI is at `cli/sahayakan_cli.py`. Usage: `python cli/sahayakan_cli.py <command>`.

## Auth

Set `AUTH_ENABLED=false` in `.env` to bypass auth in development.
