.PHONY: lint format test test-e2e run stop rebuild logs migrate setup check

PYTHON ?= python3
SVC ?= api-server

lint:
	ruff check control-plane/ data-plane/ cli/ tests/
	ruff format --check control-plane/ data-plane/ cli/ tests/

format:
	ruff format control-plane/ data-plane/ cli/ tests/
	ruff check --fix control-plane/ data-plane/ cli/ tests/

test:
	$(PYTHON) tests/unit/test_agent_contract.py
	$(PYTHON) tests/unit/test_knowledge_cache.py
	$(PYTHON) tests/unit/test_sanitize.py
	$(PYTHON) tests/unit/test_structural.py
	$(PYTHON) tests/unit/test_conventions.py

test-e2e:
	$(PYTHON) tests/test_issue_triage_e2e.py
	$(PYTHON) tests/test_stage5_e2e.py
	$(PYTHON) tests/test_stage7_e2e.py
	$(PYTHON) tests/test_stage8_e2e.py
	$(PYTHON) tests/test_stage10_e2e.py

run:
	cd infrastructure && podman-compose --env-file ../.env up -d

stop:
	cd infrastructure && podman-compose --env-file ../.env down

rebuild:
	cd infrastructure && podman-compose --env-file ../.env up -d --build $(SVC)

logs:
	podman-compose -f infrastructure/docker-compose.yml logs -f $(SVC)

migrate:
	@for f in infrastructure/db/migrations/*.sql; do \
		echo "Applying $$f..."; \
		PGPASSWORD=sahayakan_dev_password psql -h localhost -p 5433 -U sahayakan -d sahayakan -f "$$f"; \
	done

setup:
	@echo "Setting up Sahayakan development environment..."
	@test -d .venv || python3 -m venv .venv
	@. .venv/bin/activate && pip install -e ".[dev]" && pip install ruff pre-commit
	@. .venv/bin/activate && pre-commit install
	@test -f .env || cp infrastructure/.env.example .env
	@echo ""
	@echo "Setup complete! Next steps:"
	@echo "  source .venv/bin/activate"
	@echo "  make run    # start containers"
	@echo "  make test   # run unit tests"

check: lint test
