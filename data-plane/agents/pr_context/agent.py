"""PR Context Agent - Analyzes pull requests for reviewers."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from agent_runner.contracts.base_agent import AgentInput, AgentOutput, BaseAgent
from agent_runner.knowledge import KnowledgeCache
from agent_runner.logging_utils import AgentLogger
from llm_client.base import LLMClient

PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "pr_context.prompt"


class PRContextAgent(BaseAgent):
    def __init__(self, knowledge_cache: KnowledgeCache, logger: AgentLogger, llm_client: LLMClient | None = None, embedding_service=None):
        self.cache = knowledge_cache
        self.log = logger
        self.llm = llm_client
        self.embedding_service = embedding_service
        self.input: AgentInput | None = None
        self.pr_data: dict = {}
        self.context: dict = {}
        self.analysis: dict = {}
        self.llm_usage: dict = {}

    def load_input(self, agent_input: AgentInput) -> None:
        self.input = agent_input
        pr_number = agent_input.parameters.get("pr_number")
        if not pr_number:
            raise ValueError("Missing required parameter: pr_number")
        pr_path = f"github/pull_requests/{pr_number}.json"
        if not self.cache.file_exists(pr_path):
            raise ValueError(f"PR {pr_number} not found in knowledge cache. Run GitHub sync first.")
        self.pr_data = self.cache.read_json(pr_path)
        self.log.info(f"Loaded PR #{pr_number}: {self.pr_data.get('title', 'N/A')}")

    def collect_context(self) -> None:
        pr_body = (self.pr_data.get("body") or "").lower()
        pr_title = (self.pr_data.get("title") or "").lower()

        # Find linked issues from PR body/title
        issue_refs = set(int(m) for m in re.findall(r'#(\d+)', f"{pr_title} {pr_body}"))
        linked_issues = []
        for num in issue_refs:
            path = f"github/issues/{num}.json"
            if self.cache.file_exists(path):
                issue = self.cache.read_json(path)
                linked_issues.append({"number": num, "title": issue.get("title", ""), "state": issue.get("state", "")})
        self.log.info(f"Found {len(linked_issues)} linked issues")

        # Find related Jira tickets
        jira_pattern = re.compile(r'[A-Z]{2,}-\d+')
        jira_refs = set(jira_pattern.findall(f"{pr_title} {self.pr_data.get('body', '')}"))
        related_jira = []
        for key in jira_refs:
            path = f"jira/tickets/{key}.json"
            if self.cache.file_exists(path):
                ticket = self.cache.read_json(path)
                related_jira.append({"key": key, "summary": ticket.get("summary", ""), "status": ticket.get("status", "")})
        self.log.info(f"Found {len(related_jira)} related Jira tickets")

        # Find previous analyses for linked issues
        related_analyses = []
        for issue in linked_issues:
            path = f"agent_outputs/issue_analysis/{issue['number']}.json"
            if self.cache.file_exists(path):
                analysis = self.cache.read_json(path)
                related_analyses.append({"issue": issue["number"], "priority": analysis.get("priority", ""), "summary": analysis.get("summary", "")})
        self.log.info(f"Found {len(related_analyses)} previous analyses")

        self.context = {"linked_issues": linked_issues, "related_jira": related_jira, "related_analyses": related_analyses}

    def analyze(self) -> None:
        if not self.llm:
            raise RuntimeError("LLM client not configured")
        prompt_template = PROMPT_PATH.read_text()
        prompt = prompt_template.format(
            title=self.pr_data.get("title", ""),
            body=self.pr_data.get("body", "") or "No description",
            state=self.pr_data.get("state", ""),
            base_branch=self.pr_data.get("base_branch", ""),
            head_branch=self.pr_data.get("head_branch", ""),
            changed_files=self.pr_data.get("changed_files", "unknown"),
            additions=self.pr_data.get("additions", "unknown"),
            deletions=self.pr_data.get("deletions", "unknown"),
            linked_issues=json.dumps(self.context["linked_issues"], indent=2) if self.context["linked_issues"] else "None found",
            jira_tickets=json.dumps(self.context["related_jira"], indent=2) if self.context["related_jira"] else "None found",
            related_analyses=json.dumps(self.context["related_analyses"], indent=2) if self.context["related_analyses"] else "None found",
        )
        self.log.info(f"Sending prompt to LLM ({len(prompt)} chars)")
        response = self.llm.generate(prompt)
        self.log.llm(model=response.model, tokens=response.tokens_input + response.tokens_output, latency_ms=response.latency_ms)
        self.llm_usage = {"model": response.model, "tokens_input": response.tokens_input, "tokens_output": response.tokens_output, "latency_ms": response.latency_ms}

        try:
            text = response.text.strip()
            if text.startswith("```"):
                text = re.sub(r'^```\w*\n?', '', text)
                text = re.sub(r'\n?```$', '', text)
            self.analysis = json.loads(text)
        except json.JSONDecodeError as e:
            self.log.error(f"Failed to parse LLM response: {e}")
            self.analysis = {"summary": "Parse failure", "change_type": "unknown", "risk_level": "medium", "risk_reasoning": "Could not parse", "linked_issues": [], "linked_jira_tickets": [], "components_modified": [], "test_coverage_notes": "", "review_suggestions": ["Manual review required"], "breaking_changes": False, "confidence": 0.0}

        self.log.info(f"Analysis complete: risk={self.analysis.get('risk_level', '?')}, confidence={self.analysis.get('confidence', '?')}")

    def generate_output(self) -> AgentOutput:
        pr_num = self.pr_data["number"]
        output_data = {
            "pr_number": pr_num, "pr_title": self.pr_data.get("title", ""), "pr_url": self.pr_data.get("html_url", ""),
            **self.analysis, "llm_usage": self.llm_usage, "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        return AgentOutput(
            status="success", summary=self.analysis.get("summary", f"PR #{pr_num} analysis complete"), data=output_data,
            artifacts=[{"type": "pr_context_json", "path": f"agent_outputs/pr_context/{pr_num}.json"}, {"type": "pr_context_report", "path": f"agent_outputs/pr_context/{pr_num}.md"}],
        )

    def store_artifacts(self, output: AgentOutput) -> list[str]:
        pr_num = output.data["pr_number"]
        uris = []
        json_path = f"agent_outputs/pr_context/{pr_num}.json"
        self.cache.write_json(json_path, output.data)
        uris.append(json_path)
        md_path = f"agent_outputs/pr_context/{pr_num}.md"
        self.cache.write_file(md_path, self._generate_report(output.data))
        uris.append(md_path)
        self.log.info(f"Stored artifacts: {json_path}, {md_path}")
        return uris

    def _generate_report(self, data: dict) -> str:
        pr_num = data["pr_number"]
        lines = [
            f"# PR Analysis: #{pr_num} - {data.get('pr_title', '')}",
            "", f"**Generated by:** pr-context agent", f"**Date:** {data.get('generated_at', 'N/A')}", f"**Confidence:** {data.get('confidence', 0)}",
            "", "## Summary", data.get("summary", "N/A"),
            "", f"## Change Type: {data.get('change_type', 'unknown').upper()}",
            "", f"## Risk Level: {data.get('risk_level', 'unknown').upper()}", data.get("risk_reasoning", ""),
        ]
        if data.get("linked_issues"):
            lines.extend(["", "## Linked Issues"] + [f"- #{i}" for i in data["linked_issues"]])
        if data.get("linked_jira_tickets"):
            lines.extend(["", "## Linked Jira Tickets"] + [f"- {t}" for t in data["linked_jira_tickets"]])
        if data.get("components_modified"):
            lines.extend(["", "## Components Modified"] + [f"- `{c}`" for c in data["components_modified"]])
        if data.get("test_coverage_notes"):
            lines.extend(["", "## Test Coverage", data["test_coverage_notes"]])
        if data.get("review_suggestions"):
            lines.extend(["", "## Review Suggestions"] + [f"{i}. {s}" for i, s in enumerate(data["review_suggestions"], 1)])
        lines.extend(["", f"**Breaking Changes:** {'Yes' if data.get('breaking_changes') else 'No'}", "", "---", f"*Job ID: {self.input.job_id if self.input else 'N/A'}*", ""])
        return "\n".join(lines)
