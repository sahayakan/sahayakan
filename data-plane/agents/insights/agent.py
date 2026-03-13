"""Insights Agent - Detects recurring patterns across development data."""

import json
import re
from datetime import UTC, datetime
from pathlib import Path

from agent_runner.contracts.base_agent import AgentInput, AgentOutput, BaseAgent
from agent_runner.knowledge import KnowledgeCache
from agent_runner.logging_utils import AgentLogger
from llm_client.base import LLMClient

PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "insights_detection.prompt"


class InsightsAgent(BaseAgent):
    def __init__(
        self,
        knowledge_cache: KnowledgeCache,
        logger: AgentLogger,
        llm_client: LLMClient | None = None,
        embedding_service=None,
    ):
        self.cache = knowledge_cache
        self.log = logger
        self.llm = llm_client
        self.embedding_service = embedding_service
        self.input: AgentInput | None = None
        self.collected_data: dict = {}
        self.analysis: dict = {}
        self.llm_usage: dict = {}

    def load_input(self, agent_input: AgentInput) -> None:
        self.input = agent_input
        self.log.info("Insights agent initialized")

    def collect_context(self) -> None:
        # Collect all issue analyses
        issue_analyses = []
        for f in self.cache.list_files("agent_outputs/issue_analysis", "*.json"):
            try:
                data = self.cache.read_json(f)
                issue_analyses.append(
                    {
                        "issue_number": data.get("issue_number"),
                        "title": data.get("issue_title", ""),
                        "priority": data.get("priority", ""),
                        "affected_components": data.get("affected_components", []),
                        "is_duplicate": data.get("is_duplicate", False),
                        "possible_duplicates": data.get("possible_duplicates", []),
                    }
                )
            except Exception:
                pass
        self.log.info(f"Collected {len(issue_analyses)} issue analyses")

        # Collect PR analyses
        pr_analyses = []
        for f in self.cache.list_files("agent_outputs/pr_context", "*.json"):
            try:
                data = self.cache.read_json(f)
                pr_analyses.append(
                    {
                        "pr_number": data.get("pr_number"),
                        "title": data.get("pr_title", ""),
                        "risk_level": data.get("risk_level", ""),
                        "change_type": data.get("change_type", ""),
                        "components_modified": data.get("components_modified", []),
                        "breaking_changes": data.get("breaking_changes", False),
                    }
                )
            except Exception:
                pass
        self.log.info(f"Collected {len(pr_analyses)} PR analyses")

        # Collect meeting action items
        meeting_actions = []
        for f in self.cache.list_files("agent_outputs/meeting_summaries", "*.json"):
            try:
                data = self.cache.read_json(f)
                for item in data.get("action_items", []):
                    meeting_actions.append(
                        {
                            "meeting": data.get("meeting_id", f),
                            "assignee": item.get("assignee", ""),
                            "action": item.get("action", ""),
                            "related_issue": item.get("related_issue"),
                        }
                    )
            except Exception:
                pass
        self.log.info(f"Collected {len(meeting_actions)} meeting action items")

        self.collected_data = {
            "issue_analyses": issue_analyses,
            "pr_analyses": pr_analyses,
            "meeting_actions": meeting_actions,
        }

    def analyze(self) -> None:
        if not self.llm:
            raise RuntimeError("LLM client not configured")

        prompt_template = PROMPT_PATH.read_text()
        prompt = prompt_template.format(
            issue_analyses=json.dumps(self.collected_data["issue_analyses"], indent=2)[:5000]
            if self.collected_data["issue_analyses"]
            else "No issue analyses available",
            pr_analyses=json.dumps(self.collected_data["pr_analyses"], indent=2)[:3000]
            if self.collected_data["pr_analyses"]
            else "No PR analyses available",
            meeting_actions=json.dumps(self.collected_data["meeting_actions"], indent=2)[:3000]
            if self.collected_data["meeting_actions"]
            else "No meeting action items available",
        )

        self.log.info(f"Sending prompt to LLM ({len(prompt)} chars)")
        response = self.llm.generate(prompt)
        self.log.llm(
            model=response.model, tokens=response.tokens_input + response.tokens_output, latency_ms=response.latency_ms
        )
        self.llm_usage = {
            "model": response.model,
            "tokens_input": response.tokens_input,
            "tokens_output": response.tokens_output,
            "latency_ms": response.latency_ms,
        }

        try:
            text = response.text.strip()
            if text.startswith("```"):
                text = re.sub(r"^```\w*\n?", "", text)
                text = re.sub(r"\n?```$", "", text)
            self.analysis = json.loads(text)
        except json.JSONDecodeError as e:
            self.log.error(f"Failed to parse LLM response: {e}")
            self.analysis = {"insights": []}

        insights = self.analysis.get("insights", [])
        self.log.info(f"Detected {len(insights)} insights")

    def generate_output(self) -> AgentOutput:
        timestamp = datetime.now(UTC).isoformat()
        date_str = datetime.now(UTC).strftime("%Y-%m-%d")
        insights = self.analysis.get("insights", [])
        output_data = {
            "insights": insights,
            "data_summary": {
                "issues_analyzed": len(self.collected_data.get("issue_analyses", [])),
                "prs_analyzed": len(self.collected_data.get("pr_analyses", [])),
                "meeting_actions": len(self.collected_data.get("meeting_actions", [])),
            },
            "llm_usage": self.llm_usage,
            "generated_at": timestamp,
        }
        return AgentOutput(
            status="success",
            summary=f"Detected {len(insights)} insights from development data",
            data=output_data,
            artifacts=[
                {"type": "insights_json", "path": f"agent_outputs/insights/{date_str}.json"},
                {"type": "insights_report", "path": f"agent_outputs/insights/{date_str}.md"},
            ],
        )

    def store_artifacts(self, output: AgentOutput) -> list[str]:
        uris = []
        for artifact in output.artifacts:
            path = artifact["path"]
            if path.endswith(".json"):
                self.cache.write_json(path, output.data)
            else:
                self.cache.write_file(path, self._generate_report(output.data))
            uris.append(path)
        self.log.info(f"Stored {len(uris)} artifacts")
        return uris

    def _generate_report(self, data: dict) -> str:
        lines = [
            "# Insights Report",
            "",
            "**Generated by:** insights agent",
            f"**Date:** {data.get('generated_at', 'N/A')}",
            f"**Data:** {data['data_summary']['issues_analyzed']} issues, "
            f"{data['data_summary']['prs_analyzed']} PRs, "
            f"{data['data_summary']['meeting_actions']} action items",
            "",
        ]
        insights = data.get("insights", [])
        if not insights:
            lines.append("No significant insights detected.")
        for i, ins in enumerate(insights, 1):
            severity = ins.get("severity", "medium").upper()
            lines.extend(
                [
                    f"## {i}. {ins.get('title', 'Untitled')}",
                    f"**Type:** {ins.get('insight_type', '?')} | **Severity:** {severity} | **Confidence:** {ins.get('confidence', 0):.0%}",
                    "",
                    ins.get("description", ""),
                ]
            )
            evidence = ins.get("evidence", [])
            if evidence:
                lines.append("\n**Evidence:**")
                for ev in evidence:
                    lines.append(f"- {ev.get('type', '?')} #{ev.get('id', '?')}: {ev.get('detail', '')}")
            lines.append("")
        lines.extend(["---", f"*Job ID: {self.input.job_id if self.input else 'N/A'}*", ""])
        return "\n".join(lines)
