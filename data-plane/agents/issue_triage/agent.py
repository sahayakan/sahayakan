"""Issue Triage Agent - Analyzes GitHub issues for priority, duplicates, and related items."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from agent_runner.contracts.base_agent import (
    AgentInput,
    AgentOutput,
    BaseAgent,
)
from agent_runner.knowledge import KnowledgeCache
from agent_runner.logging_utils import AgentLogger
from llm_client.base import LLMClient


PROMPT_TEMPLATE_PATH = Path(__file__).parent.parent.parent / "prompts" / "issue_analysis.prompt"


class IssueTriageAgent(BaseAgent):
    def __init__(
        self,
        knowledge_cache: KnowledgeCache,
        logger: AgentLogger,
        llm_client: LLMClient | None = None,
    ):
        self.cache = knowledge_cache
        self.log = logger
        self.llm = llm_client
        self.input: AgentInput | None = None
        self.issue_data: dict = {}
        self.context: dict = {}
        self.analysis: dict = {}
        self.llm_usage: dict = {}

    def load_input(self, agent_input: AgentInput) -> None:
        self.input = agent_input
        issue_id = agent_input.parameters.get("issue_id")
        if not issue_id:
            raise ValueError("Missing required parameter: issue_id")

        issue_path = f"github/issues/{issue_id}.json"
        if not self.cache.file_exists(issue_path):
            raise ValueError(
                f"Issue {issue_id} not found in knowledge cache. "
                f"Run GitHub sync first."
            )

        self.issue_data = self.cache.read_json(issue_path)
        self.log.info(
            f"Loaded issue #{issue_id}: {self.issue_data.get('title', 'N/A')}"
        )

    def collect_context(self) -> None:
        issue_num = self.issue_data["number"]
        issue_title = self.issue_data.get("title", "").lower()
        issue_body = (self.issue_data.get("body") or "").lower()
        keywords = set(
            re.findall(r'\b[a-z]{3,}\b', f"{issue_title} {issue_body}")
        )

        # Find previous issue analyses
        similar_issues = []
        analysis_files = self.cache.list_files(
            "agent_outputs/issue_analysis", "*.json"
        )
        for f in analysis_files:
            try:
                analysis = self.cache.read_json(f)
                if analysis.get("issue_number") != issue_num:
                    similar_issues.append({
                        "number": analysis.get("issue_number"),
                        "summary": analysis.get("summary", ""),
                        "priority": analysis.get("priority", ""),
                    })
            except Exception:
                pass
        self.log.info(f"Found {len(similar_issues)} previous analyses")

        # Find related PRs by scanning PR data
        related_prs = []
        pr_files = self.cache.list_files(
            "github/pull_requests", "*.json"
        )
        for f in pr_files:
            try:
                pr = self.cache.read_json(f)
                pr_title = (pr.get("title") or "").lower()
                pr_body = (pr.get("body") or "").lower()
                pr_text = f"{pr_title} {pr_body}"

                # Check if PR references this issue
                if f"#{issue_num}" in pr_text:
                    related_prs.append({
                        "number": pr["number"],
                        "title": pr.get("title", ""),
                        "state": pr.get("state", ""),
                    })
                    continue

                # Check keyword overlap
                pr_keywords = set(re.findall(r'\b[a-z]{3,}\b', pr_text))
                overlap = keywords & pr_keywords
                if len(overlap) > 5:
                    related_prs.append({
                        "number": pr["number"],
                        "title": pr.get("title", ""),
                        "state": pr.get("state", ""),
                    })
            except Exception:
                pass
        self.log.info(f"Found {len(related_prs)} related PRs")

        # Find related Jira tickets
        related_jira = []
        jira_files = self.cache.list_files("jira/tickets", "*.json")
        for f in jira_files:
            try:
                ticket = self.cache.read_json(f)
                ticket_text = (
                    f"{ticket.get('summary', '')} "
                    f"{ticket.get('description', '')}"
                ).lower()

                # Check if issue body mentions this ticket
                ticket_key = ticket.get("key", "")
                if ticket_key and ticket_key.lower() in issue_body:
                    related_jira.append({
                        "key": ticket_key,
                        "summary": ticket.get("summary", ""),
                        "status": ticket.get("status", ""),
                    })
                    continue

                # Check keyword overlap
                jira_keywords = set(
                    re.findall(r'\b[a-z]{3,}\b', ticket_text)
                )
                overlap = keywords & jira_keywords
                if len(overlap) > 5:
                    related_jira.append({
                        "key": ticket_key,
                        "summary": ticket.get("summary", ""),
                        "status": ticket.get("status", ""),
                    })
            except Exception:
                pass
        self.log.info(f"Found {len(related_jira)} related Jira tickets")

        self.context = {
            "similar_issues": similar_issues[:10],
            "related_prs": related_prs[:10],
            "related_jira": related_jira[:10],
        }

    def analyze(self) -> None:
        if not self.llm:
            raise RuntimeError("LLM client not configured")

        # Build prompt
        prompt_template = PROMPT_TEMPLATE_PATH.read_text()

        # Format comments
        comments_text = "None"
        if self.issue_data.get("comments"):
            comments_text = "\n".join(
                f"- {c.get('user', '?')}: {c.get('body', '')[:200]}"
                for c in self.issue_data["comments"][:10]
            )

        prompt = prompt_template.format(
            title=self.issue_data.get("title", ""),
            body=self.issue_data.get("body", "") or "No description",
            labels=", ".join(self.issue_data.get("labels", [])) or "None",
            comments=comments_text,
            similar_issues=json.dumps(
                self.context["similar_issues"], indent=2
            )
            if self.context["similar_issues"]
            else "None found",
            related_prs=json.dumps(
                self.context["related_prs"], indent=2
            )
            if self.context["related_prs"]
            else "None found",
            jira_tickets=json.dumps(
                self.context["related_jira"], indent=2
            )
            if self.context["related_jira"]
            else "None found",
        )

        self.log.info(
            f"Sending prompt to LLM ({len(prompt)} chars)"
        )
        response = self.llm.generate(prompt)

        self.log.llm(
            model=response.model,
            tokens=response.tokens_input + response.tokens_output,
            latency_ms=response.latency_ms,
        )

        self.llm_usage = {
            "model": response.model,
            "tokens_input": response.tokens_input,
            "tokens_output": response.tokens_output,
            "latency_ms": response.latency_ms,
        }

        # Parse JSON response
        try:
            text = response.text.strip()
            # Strip markdown code fences if present
            if text.startswith("```"):
                text = re.sub(r'^```\w*\n?', '', text)
                text = re.sub(r'\n?```$', '', text)
            self.analysis = json.loads(text)
        except json.JSONDecodeError as e:
            self.log.error(f"Failed to parse LLM response as JSON: {e}")
            self.analysis = {
                "summary": "Analysis failed - could not parse LLM response",
                "priority": "medium",
                "priority_reasoning": "Default priority due to parse failure",
                "is_duplicate": False,
                "possible_duplicates": [],
                "related_prs": [],
                "related_jira_tickets": [],
                "affected_components": [],
                "suggested_labels": [],
                "suggested_actions": ["Manual review required"],
                "confidence": 0.0,
                "parse_error": str(e),
                "raw_response": response.text[:500],
            }

        self.log.info(
            f"Analysis complete: priority={self.analysis.get('priority', '?')}, "
            f"confidence={self.analysis.get('confidence', '?')}"
        )

    def generate_output(self) -> AgentOutput:
        issue_num = self.issue_data["number"]
        timestamp = datetime.now(timezone.utc).isoformat()

        output_data = {
            "issue_number": issue_num,
            "issue_title": self.issue_data.get("title", ""),
            "issue_url": self.issue_data.get("html_url", ""),
            **self.analysis,
            "context_used": {
                "similar_issues_count": len(
                    self.context.get("similar_issues", [])
                ),
                "related_prs_count": len(
                    self.context.get("related_prs", [])
                ),
                "related_jira_count": len(
                    self.context.get("related_jira", [])
                ),
            },
            "llm_usage": self.llm_usage,
            "generated_at": timestamp,
        }

        return AgentOutput(
            status="success",
            summary=self.analysis.get(
                "summary",
                f"Issue #{issue_num} analysis complete",
            ),
            data=output_data,
            artifacts=[
                {
                    "type": "issue_analysis_json",
                    "path": f"agent_outputs/issue_analysis/{issue_num}.json",
                },
                {
                    "type": "issue_analysis_report",
                    "path": f"agent_outputs/issue_analysis/{issue_num}.md",
                },
            ],
        )

    def store_artifacts(self, output: AgentOutput) -> list[str]:
        issue_num = output.data["issue_number"]
        uris = []

        # Store JSON
        json_path = f"agent_outputs/issue_analysis/{issue_num}.json"
        self.cache.write_json(json_path, output.data)
        uris.append(json_path)
        self.log.info(f"Stored JSON: {json_path}")

        # Generate and store Markdown report
        md_path = f"agent_outputs/issue_analysis/{issue_num}.md"
        report = self._generate_markdown_report(output.data)
        self.cache.write_file(md_path, report)
        uris.append(md_path)
        self.log.info(f"Stored report: {md_path}")

        return uris

    def _generate_markdown_report(self, data: dict) -> str:
        issue_num = data["issue_number"]
        title = data.get("issue_title", "Unknown")
        priority = data.get("priority", "unknown").upper()
        confidence = data.get("confidence", 0)

        lines = [
            f"# Issue Analysis: #{issue_num} - {title}",
            "",
            f"**Generated by:** issue-triage agent",
            f"**Date:** {data.get('generated_at', 'N/A')}",
            f"**Confidence:** {confidence}",
            "",
            "## Summary",
            data.get("summary", "No summary available"),
            "",
            f"## Priority: {priority}",
            data.get("priority_reasoning", "No reasoning provided"),
            "",
        ]

        # Duplicates
        if data.get("is_duplicate") or data.get("possible_duplicates"):
            lines.append("## Possible Duplicates")
            if data.get("possible_duplicates"):
                for dup in data["possible_duplicates"]:
                    lines.append(f"- #{dup}")
            else:
                lines.append("- None detected")
            lines.append("")

        # Related PRs
        related_prs = data.get("related_prs", [])
        if related_prs:
            lines.append("## Related PRs")
            for pr in related_prs:
                if isinstance(pr, dict):
                    lines.append(f"- #{pr.get('number', pr)}")
                else:
                    lines.append(f"- #{pr}")
            lines.append("")

        # Jira tickets
        jira_tickets = data.get("related_jira_tickets", [])
        if jira_tickets:
            lines.append("## Related Jira Tickets")
            for ticket in jira_tickets:
                lines.append(f"- {ticket}")
            lines.append("")

        # Components
        components = data.get("affected_components", [])
        if components:
            lines.append("## Affected Components")
            for comp in components:
                lines.append(f"- {comp}")
            lines.append("")

        # Suggested labels
        labels = data.get("suggested_labels", [])
        if labels:
            lines.append("## Suggested Labels")
            lines.append(", ".join(f"`{l}`" for l in labels))
            lines.append("")

        # Suggested actions
        actions = data.get("suggested_actions", [])
        if actions:
            lines.append("## Suggested Actions")
            for i, action in enumerate(actions, 1):
                lines.append(f"{i}. {action}")
            lines.append("")

        lines.extend([
            "---",
            f"*Job ID: {self.input.job_id if self.input else 'N/A'}*",
        ])

        return "\n".join(lines) + "\n"
