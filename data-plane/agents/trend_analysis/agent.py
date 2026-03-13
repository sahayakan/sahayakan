"""Trend Analysis Agent - Produces periodic trend reports."""

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from agent_runner.contracts.base_agent import AgentInput, AgentOutput, BaseAgent
from agent_runner.knowledge import KnowledgeCache
from agent_runner.logging_utils import AgentLogger
from llm_client.base import LLMClient

PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "trend_analysis.prompt"


class TrendAnalysisAgent(BaseAgent):
    def __init__(self, knowledge_cache: KnowledgeCache, logger: AgentLogger, llm_client: LLMClient | None = None, embedding_service=None):
        self.cache = knowledge_cache
        self.log = logger
        self.llm = llm_client
        self.embedding_service = embedding_service
        self.input: AgentInput | None = None
        self.metrics: dict = {}
        self.analysis: dict = {}
        self.llm_usage: dict = {}

    def load_input(self, agent_input: AgentInput) -> None:
        self.input = agent_input
        self.log.info("Trend analysis agent initialized")

    def collect_context(self) -> None:
        # Compute metrics from existing analyses
        priority_counter = Counter()
        risk_counter = Counter()
        component_counter = Counter()
        recent_issues = []
        recent_prs = []

        for f in self.cache.list_files("agent_outputs/issue_analysis", "*.json"):
            try:
                data = self.cache.read_json(f)
                priority_counter[data.get("priority", "unknown")] += 1
                for comp in data.get("affected_components", []):
                    component_counter[comp] += 1
                recent_issues.append({
                    "number": data.get("issue_number"),
                    "priority": data.get("priority"),
                    "components": data.get("affected_components", []),
                })
            except Exception:
                pass

        for f in self.cache.list_files("agent_outputs/pr_context", "*.json"):
            try:
                data = self.cache.read_json(f)
                risk_counter[data.get("risk_level", "unknown")] += 1
                recent_prs.append({
                    "number": data.get("pr_number"),
                    "risk": data.get("risk_level"),
                    "type": data.get("change_type"),
                })
            except Exception:
                pass

        total_meetings = len(self.cache.list_files("agent_outputs/meeting_summaries", "*.json"))

        self.metrics = {
            "total_issues": len(recent_issues),
            "total_prs": len(recent_prs),
            "total_meetings": total_meetings,
            "priority_distribution": dict(priority_counter),
            "risk_distribution": dict(risk_counter),
            "component_frequency": dict(component_counter.most_common(15)),
            "recent_issues": recent_issues[-10:],
            "recent_prs": recent_prs[-10:],
        }
        self.log.info(f"Metrics: {self.metrics['total_issues']} issues, {self.metrics['total_prs']} PRs, {self.metrics['total_meetings']} meetings")

    def analyze(self) -> None:
        if not self.llm:
            raise RuntimeError("LLM client not configured")

        prompt_template = PROMPT_PATH.read_text()
        recent = json.dumps({"issues": self.metrics["recent_issues"], "prs": self.metrics["recent_prs"]}, indent=2)
        prompt = prompt_template.format(
            total_issues=self.metrics["total_issues"],
            total_prs=self.metrics["total_prs"],
            total_meetings=self.metrics["total_meetings"],
            priority_distribution=json.dumps(self.metrics["priority_distribution"], indent=2),
            risk_distribution=json.dumps(self.metrics["risk_distribution"], indent=2),
            component_frequency=json.dumps(self.metrics["component_frequency"], indent=2),
            recent_activity=recent[:3000],
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
            self.analysis = {"summary": "Parse failure", "issue_trends": [], "risk_areas": [], "positive_signals": [], "recommendations": [], "health_score": 0.5}

        self.log.info(f"Trends: health_score={self.analysis.get('health_score', '?')}, {len(self.analysis.get('recommendations', []))} recommendations")

    def generate_output(self) -> AgentOutput:
        timestamp = datetime.now(timezone.utc).isoformat()
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        output_data = {**self.analysis, "metrics": self.metrics, "llm_usage": self.llm_usage, "generated_at": timestamp}
        return AgentOutput(
            status="success",
            summary=self.analysis.get("summary", "Trend analysis complete"),
            data=output_data,
            artifacts=[
                {"type": "trend_json", "path": f"agent_outputs/trends/{date_str}.json"},
                {"type": "trend_report", "path": f"agent_outputs/trends/{date_str}.md"},
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
        metrics = data.get("metrics", {})
        lines = [
            "# Development Trend Report",
            "", f"**Generated by:** trend-analysis agent",
            f"**Date:** {data.get('generated_at', 'N/A')}",
            f"**Health Score:** {data.get('health_score', 0):.0%}",
            "", f"**Data:** {metrics.get('total_issues', 0)} issues, {metrics.get('total_prs', 0)} PRs, {metrics.get('total_meetings', 0)} meetings",
            "", "## Summary", data.get("summary", "N/A"),
        ]
        if data.get("issue_trends"):
            lines.extend(["", "## Issue Trends"])
            for t in data["issue_trends"]:
                lines.append(f"- **{t.get('component', '?')}**: {t.get('trend', '?')} - {t.get('detail', '')}")
        if data.get("risk_areas"):
            lines.extend(["", "## Risk Areas"] + [f"- {r}" for r in data["risk_areas"]])
        if data.get("positive_signals"):
            lines.extend(["", "## Positive Signals"] + [f"- {s}" for s in data["positive_signals"]])
        if data.get("recommendations"):
            lines.extend(["", "## Recommendations"] + [f"{i}. {r}" for i, r in enumerate(data["recommendations"], 1)])
        if metrics.get("priority_distribution"):
            lines.extend(["", "## Priority Distribution"] + [f"- {k}: {v}" for k, v in metrics["priority_distribution"].items()])
        if metrics.get("risk_distribution"):
            lines.extend(["", "## Risk Distribution"] + [f"- {k}: {v}" for k, v in metrics["risk_distribution"].items()])
        lines.extend(["", "---", f"*Job ID: {self.input.job_id if self.input else 'N/A'}*", ""])
        return "\n".join(lines)
