#!/usr/bin/env python3
"""End-to-end test: Ingest test-project issues from GitHub, then run Issue Triage agent."""

import json
import os
import subprocess
import sys
import tempfile
import time

# Setup paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "data-plane"))
sys.path.insert(0, PROJECT_ROOT)

from agent_runner.contracts.base_agent import AgentInput
from agent_runner.knowledge import KnowledgeCache
from agent_runner.logging_utils import AgentLogger
from agents.issue_triage.agent import IssueTriageAgent
from ingestion.github_fetcher.fetcher import GitHubFetcher
from ingestion.github_fetcher.token_provider import GitHubTokenProvider
from llm_client.base import LLMClient, LLMResponse


class GeminiAPIClient(LLMClient):
    """LLM client using Google Gemini via the REST API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model = "gemini-2.0-flash"
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

    def generate(self, prompt: str, model: str | None = None) -> LLMResponse:
        import urllib.request

        url = f"{self.api_url}?key={self.api_key}"
        payload = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
        })

        req = urllib.request.Request(
            url,
            data=payload.encode(),
            headers={"Content-Type": "application/json"},
        )

        start = time.monotonic()
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode())
        latency_ms = int((time.monotonic() - start) * 1000)

        text = result["candidates"][0]["content"]["parts"][0]["text"]
        usage = result.get("usageMetadata", {})

        return LLMResponse(
            text=text,
            model=model or self.model,
            tokens_input=usage.get("promptTokenCount", 0),
            tokens_output=usage.get("candidatesTokenCount", 0),
            latency_ms=latency_ms,
        )


class CLITokenProvider(GitHubTokenProvider):
    """Token provider that uses `gh auth token` for local dev/test."""

    def get_token(self) -> str:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            result = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
            token = result.stdout.strip()
        if not token:
            raise RuntimeError("No GitHub token available (set GITHUB_TOKEN or install gh CLI)")
        return token


def main():
    # Use a temp directory for knowledge cache
    cache_dir = tempfile.mkdtemp(prefix="sahayakan-triage-test-")
    print(f"Knowledge cache: {cache_dir}")

    cache = KnowledgeCache(cache_dir)

    # Step 1: Ingest issues and PRs from test-project
    print("\n" + "=" * 60)
    print("STEP 1: Ingesting from sahayakan/test-project")
    print("=" * 60)

    fetcher = GitHubFetcher(token_provider=CLITokenProvider(), knowledge_cache=cache)
    result = fetcher.sync_repo(owner="sahayakan", repo="test-project")
    print(f"Issues synced: {result.issues_synced}")
    print(f"PRs synced: {result.prs_synced}")
    if result.errors:
        print(f"Errors: {result.errors}")

    # List what we ingested
    issues = cache.list_files("github/issues", "*.json")
    prs = cache.list_files("github/pull_requests", "*.json")
    print(f"\nCached issues: {issues}")
    print(f"Cached PRs: {prs}")

    # Step 2: Run Issue Triage agent on each issue
    print("\n" + "=" * 60)
    print("STEP 2: Running Issue Triage Agent")
    print("=" * 60)

    gemini_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        print("ERROR: GEMINI_API_KEY not set")
        sys.exit(1)
    llm = GeminiAPIClient(api_key=gemini_key)
    logger = AgentLogger(job_id=0)

    for issue_file in sorted(issues):
        issue_data = cache.read_json(issue_file)
        issue_num = issue_data["number"]
        print(f"\n--- Issue #{issue_num}: {issue_data['title']} ---")

        agent = IssueTriageAgent(
            knowledge_cache=cache,
            logger=logger,
            llm_client=llm,
        )

        try:
            agent_input = AgentInput(
                job_id=issue_num,
                agent_name="issue-triage",
                source="test-script",
                parameters={"issue_id": str(issue_num)},
            )

            agent.load_input(agent_input)
            agent.collect_context()
            agent.analyze()
            output = agent.generate_output()
            agent.store_artifacts(output)

            analysis = output.data
            print(f"  Priority: {analysis.get('priority', '?')}")
            print(f"  Summary: {analysis.get('summary', '?')}")
            print(f"  Labels: {analysis.get('suggested_labels', [])}")
            print(f"  Confidence: {analysis.get('confidence', '?')}")
            print(f"  LLM tokens: {analysis.get('llm_usage', {}).get('tokens_input', 0)}in / {analysis.get('llm_usage', {}).get('tokens_output', 0)}out")
        except Exception as e:
            print(f"  ERROR: {e}")

    # Step 3: Show all analysis reports
    print("\n" + "=" * 60)
    print("STEP 3: Analysis Reports")
    print("=" * 60)

    reports = cache.list_files("agent_outputs/issue_analysis", "*.md")
    for report_file in sorted(reports):
        print(f"\n{'=' * 60}")
        print(cache.read_file(report_file))

    print(f"\nAll outputs stored in: {cache_dir}/agent_outputs/issue_analysis/")


if __name__ == "__main__":
    main()
