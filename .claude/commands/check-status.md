Check the health and status of the Sahayakan platform.

Run the following checks and report results:

1. **Container status**: Run `podman-compose -f infrastructure/docker-compose.yml ps` to see which services are running.

2. **API health**: Run `curl -s http://localhost:8000/health` to check the API server health endpoint.

3. **Database connectivity**: Run `psql -h localhost -p 5433 -U sahayakan -d sahayakan -c "SELECT count(*) FROM agents;"` to verify DB access (use PGPASSWORD=sahayakan_dev_password).

4. **Recent jobs**: Run `psql -h localhost -p 5433 -U sahayakan -d sahayakan -c "SELECT id, agent_name, status, created_at FROM jobs ORDER BY created_at DESC LIMIT 5;"` to show recent job activity.

5. **Registered agents**: Run `curl -s http://localhost:8000/agents` to list registered agents.

Summarize the overall platform health based on these results.
