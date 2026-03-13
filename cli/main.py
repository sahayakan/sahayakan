"""Sahayakan CLI - command-line tool for the agent platform."""

import json

import click

from cli import api_client as api


@click.group()
def cli():
    """Sahayakan - Agentic AI platform for software teams."""
    pass


# --- System ---


@cli.command()
def status():
    """Show system health status."""
    data = api.get("/health")
    click.echo(f"Status:   {data['status']}")
    click.echo(f"Database: {data['database']}")
    click.echo(f"Version:  {data['version']}")


@cli.command()
def usage():
    """Show LLM usage summary."""
    data = api.get("/usage/summary")
    click.echo(f"Total runs:      {data.get('total_runs', 0)}")
    click.echo(f"Total tokens in: {data.get('total_tokens_input', 0):,}")
    click.echo(f"Total tokens out:{data.get('total_tokens_output', 0):,}")
    click.echo(f"Estimated cost:  ${data.get('total_estimated_cost', 0):.4f}")


# --- Agent commands ---


@cli.group()
def agent():
    """Manage agents."""
    pass


@agent.command("list")
def agent_list():
    """List registered agents."""
    agents = api.get("/agents")
    if not agents:
        click.echo("No agents registered.")
        return
    click.echo(f"{'Name':<20} {'Version':<10} {'Description'}")
    click.echo("-" * 60)
    for a in agents:
        click.echo(f"{a['name']:<20} {a['version']:<10} {a.get('description', '')}")


@agent.command("info")
@click.argument("name")
def agent_info(name):
    """Show agent details."""
    a = api.get(f"/agents/{name}")
    click.echo(f"Name:        {a['name']}")
    click.echo(f"Version:     {a['version']}")
    click.echo(f"Description: {a.get('description', 'N/A')}")
    click.echo(f"Image:       {a.get('container_image', 'N/A')}")
    click.echo(f"Created:     {a['created_at']}")


@agent.command("gates")
@click.argument("name")
@click.option("--set", "set_gate", help="Set gate: stage=true/false")
def agent_gates(name, set_gate):
    """Show or configure review gates."""
    if set_gate:
        stage, value = set_gate.split("=")
        enabled = value.lower() in ("true", "1", "yes")
        api.put(f"/agents/{name}/gates", [{"stage": stage, "enabled": enabled}])
        click.echo(f"Gate '{stage}' {'enabled' if enabled else 'disabled'} for {name}")
    gates = api.get(f"/agents/{name}/gates")
    if not gates:
        click.echo("No review gates configured.")
        return
    for g in gates:
        status = click.style("ON", fg="yellow") if g["enabled"] else click.style("OFF", fg="white")
        click.echo(f"  {g['stage']:<20} {status}")


# --- Run commands ---


@cli.command()
@click.argument("agent_name")
@click.option("--issue", type=int, help="GitHub issue number")
@click.option("--pr", type=int, help="PR number")
@click.option("--transcript", help="Transcript ID")
@click.option("--param", multiple=True, help="Extra params as key=value")
def run(agent_name, issue, pr, transcript, param):
    """Run an agent."""
    params = {}
    if issue:
        params["issue_id"] = issue
    if pr:
        params["pr_number"] = pr
    if transcript:
        params["transcript_id"] = transcript
    for p in param:
        k, v = p.split("=", 1)
        params[k] = v

    result = api.post("/jobs/run", {"agent": agent_name, "parameters": params})
    click.echo(f"Job #{result['id']} created ({result['status']})")


# --- Job commands ---


@cli.group()
def job():
    """Manage jobs."""
    pass


@job.command("list")
@click.option("--status", "status_filter", help="Filter by status")
@click.option("--limit", default=20, help="Max results")
def job_list(status_filter, limit):
    """List jobs."""
    path = f"/jobs?limit={limit}"
    if status_filter:
        path += f"&status={status_filter}"
    jobs = api.get(path)
    click.echo(f"{'ID':<6} {'Agent':<20} {'Status':<18} {'Created'}")
    click.echo("-" * 70)
    for j in jobs:
        click.echo(f"{j['id']:<6} {j['agent_name']:<20} {j['status']:<18} {j['created_at'][:19]}")


@job.command("status")
@click.argument("job_id", type=int)
def job_status(job_id):
    """Show job details."""
    j = api.get(f"/jobs/{job_id}")
    click.echo(f"Job #{j['id']}")
    click.echo(f"Agent:     {j['agent_name']}")
    click.echo(f"Status:    {j['status']}")
    click.echo(f"Params:    {json.dumps(j.get('parameters', {}))}")
    click.echo(f"Created:   {j['created_at']}")
    click.echo(f"Started:   {j.get('started_at') or '-'}")
    click.echo(f"Completed: {j.get('completed_at') or '-'}")


@job.command("logs")
@click.argument("job_id", type=int)
@click.option("--limit", default=100, help="Max log lines")
def job_logs(job_id, limit):
    """Show job logs."""
    data = api.get(f"/logs/{job_id}?limit={limit}")
    for entry in data.get("logs", []):
        ts = entry.get("timestamp", "")[:23]
        level = entry.get("level", "INFO")
        msg = entry.get("message", "")
        click.echo(f"[{level}] {ts} {msg}")
    if not data.get("logs"):
        click.echo("No logs available.")


@job.command("review")
@click.argument("job_id", type=int)
@click.option("--approve", is_flag=True, help="Approve the job")
@click.option("--reject", "reject_reason", help="Reject with reason")
@click.option("--comment", default="", help="Review comment")
def job_review(job_id, approve, reject_reason, comment):
    """Submit a review decision for a paused job."""
    if not approve and not reject_reason:
        click.echo("Specify --approve or --reject 'reason'")
        return
    decision = "approved" if approve else "rejected"
    comments = comment or reject_reason or ""
    result = api.post(
        f"/jobs/{job_id}/review",
        {
            "decision": decision,
            "comments": comments,
        },
    )
    click.echo(f"Job #{job_id}: {result.get('decision', decision)} at stage '{result.get('stage', '?')}'")


# --- Sync commands ---


@cli.group()
def sync():
    """Data ingestion commands."""
    pass


@sync.command("github")
@click.argument("owner")
@click.argument("repo")
def sync_github(owner, repo):
    """Trigger GitHub sync for a repository."""
    result = api.post("/ingestion/github/sync", {"owner": owner, "repo": repo})
    click.echo(f"Status:  {result['status']}")
    click.echo(f"Issues:  {result['issues_synced']}")
    click.echo(f"PRs:     {result['prs_synced']}")
    if result.get("errors"):
        for e in result["errors"]:
            click.echo(f"Error:   {e}")


@sync.command("status")
def sync_status():
    """Show ingestion status."""
    gh = api.get("/ingestion/github/status")
    jira = api.get("/ingestion/jira/status")
    click.echo(f"GitHub issues cached:  {gh['issues_cached']}")
    click.echo(f"GitHub PRs cached:     {gh['prs_cached']}")
    click.echo(f"Jira tickets cached:   {jira['tickets_cached']}")


# --- Report commands ---


@cli.group()
def report():
    """Browse reports."""
    pass


@report.command("list")
@click.option("--type", "report_type", help="Filter by report type")
def report_list(report_type):
    """List generated reports."""
    path = "/knowledge/reports"
    if report_type:
        path += f"?report_type={report_type}"
    data = api.get(path)
    reports = data.get("reports", [])
    if not reports:
        click.echo("No reports yet.")
        return
    click.echo(f"{'Type':<25} {'ID'}")
    click.echo("-" * 50)
    for r in reports:
        click.echo(f"{r['type']:<25} {r['id']}")


@report.command("view")
@click.argument("report_type")
@click.argument("report_id")
@click.option("--json", "show_json", is_flag=True, help="Show raw JSON instead of markdown")
def report_view(report_type, report_id, show_json):
    """View a report."""
    data = api.get(f"/knowledge/reports/{report_type}/{report_id}")
    if show_json and "data" in data:
        click.echo(json.dumps(data["data"], indent=2))
    elif "markdown" in data:
        click.echo(data["markdown"])
    else:
        click.echo("No report content available.")


# --- Events commands ---


@cli.group()
def events():
    """Browse events."""
    pass


@events.command("list")
@click.option("--limit", default=20)
@click.option("--type", "event_type", help="Filter by event type")
def events_list(limit, event_type):
    """List recent events."""
    path = f"/events?limit={limit}"
    if event_type:
        path += f"&event_type={event_type}"
    data = api.get(path)
    click.echo(f"{'ID':<6} {'Type':<25} {'Source':<20} {'Created'}")
    click.echo("-" * 75)
    for e in data.get("events", []):
        click.echo(f"{e['id']:<6} {e['event_type']:<25} {e['source']:<20} {e['created_at'][:19]}")


# --- Knowledge commands ---


@cli.group()
def knowledge():
    """Knowledge base operations."""
    pass


@knowledge.command("search")
@click.argument("query")
@click.option("--type", "source_type", multiple=True, help="Filter by type (issue, pr, jira, report)")
@click.option("--limit", default=10)
def knowledge_search(query, source_type, limit):
    """Semantic search across the knowledge base."""
    body = {"query": query, "limit": limit}
    if source_type:
        body["types"] = list(source_type)
    data = api.post("/knowledge/search", body)
    results = data.get("results", [])
    if not results:
        click.echo("No results found.")
        if data.get("total_embeddings", 0) == 0:
            click.echo("Hint: run 'sahayakan knowledge backfill' to index existing content.")
        return
    click.echo(f"{'Score':<8} {'Type':<10} {'ID':<20} {'Info'}")
    click.echo("-" * 65)
    for r in results:
        meta = r.get("metadata") or {}
        info = meta.get("title") or meta.get("summary") or ""
        click.echo(f"{r['similarity']:<8.3f} {r['source_type']:<10} {r['source_id']:<20} {info[:30]}")


@knowledge.command("stats")
def knowledge_stats():
    """Show embedding statistics."""
    data = api.get("/knowledge/search/stats")
    click.echo(f"Total embeddings: {data.get('total_embeddings', 0)}")
    for t, c in data.get("by_type", {}).items():
        click.echo(f"  {t}: {c}")


# --- Schedule commands ---


@cli.group()
def schedule():
    """Manage scheduled jobs."""
    pass


@schedule.command("list")
def schedule_list():
    """List all schedules."""
    data = api.get("/schedules")
    schedules = data.get("schedules", [])
    if not schedules:
        click.echo("No schedules configured.")
        return
    click.echo(f"{'ID':<5} {'Name':<25} {'Type':<15} {'Cron':<20} {'Enabled':<8} {'Next Run'}")
    click.echo("-" * 95)
    for s in schedules:
        next_run = s.get("next_run_at", "-")
        if next_run and next_run != "-":
            next_run = next_run[:19]
        click.echo(
            f"{s['id']:<5} {s['name']:<25} {s['schedule_type']:<15} {s['cron_expression']:<20} {'Yes' if s['enabled'] else 'No':<8} {next_run}"
        )


@schedule.command("create")
@click.argument("name")
@click.option("--agent", help="Agent name (for agent_job type)")
@click.option("--type", "stype", default="agent_job", help="Schedule type")
@click.option("--cron", required=True, help="Cron expression (e.g., '*/10 * * * *')")
@click.option("--param", multiple=True, help="Parameters as key=value")
def schedule_create(name, agent, stype, cron, param):
    """Create a new schedule."""
    params = {}
    for p in param:
        k, v = p.split("=", 1)
        params[k] = v
    body = {
        "name": name,
        "agent_name": agent,
        "schedule_type": stype,
        "cron_expression": cron,
        "parameters": params,
    }
    result = api.post("/schedules", body)
    click.echo(f"Schedule #{result['id']} created: {result['name']}")
    click.echo(f"Next run: {result.get('next_run_at', 'N/A')}")


@schedule.command("delete")
@click.argument("schedule_id", type=int)
def schedule_delete(schedule_id):
    """Delete a schedule."""
    api.post(f"/schedules/{schedule_id}", None)  # Will use DELETE via direct call
    # Actually need to use a different approach since api_client only has get/post/put
    import urllib.request

    req = urllib.request.Request(f"{api.API_URL}/schedules/{schedule_id}", method="DELETE")
    try:
        urllib.request.urlopen(req)
        click.echo(f"Schedule #{schedule_id} deleted.")
    except Exception as e:
        click.echo(f"Error: {e}")


@schedule.command("toggle")
@click.argument("schedule_id", type=int)
@click.option("--enable/--disable", default=True)
def schedule_toggle(schedule_id, enable):
    """Enable or disable a schedule."""
    api.put(f"/schedules/{schedule_id}", {"enabled": enable})
    click.echo(f"Schedule #{schedule_id} {'enabled' if enable else 'disabled'}.")


if __name__ == "__main__":
    cli()
