"""Meeting Summary Agent - Extracts action items and decisions from transcripts."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from agent_runner.contracts.base_agent import AgentInput, AgentOutput, BaseAgent
from agent_runner.knowledge import KnowledgeCache
from agent_runner.logging_utils import AgentLogger
from llm_client.base import LLMClient

PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "meeting_summary.prompt"


class MeetingSummaryAgent(BaseAgent):
    def __init__(self, knowledge_cache: KnowledgeCache, logger: AgentLogger, llm_client: LLMClient | None = None):
        self.cache = knowledge_cache
        self.log = logger
        self.llm = llm_client
        self.input: AgentInput | None = None
        self.transcript_id: str = ""
        self.transcript_text: str = ""
        self.context: dict = {}
        self.analysis: dict = {}
        self.llm_usage: dict = {}

    def load_input(self, agent_input: AgentInput) -> None:
        self.input = agent_input
        self.transcript_id = agent_input.parameters.get("transcript_id", "")
        if not self.transcript_id:
            raise ValueError("Missing required parameter: transcript_id")

        # Try .txt first, then .md
        for ext in (".txt", ".md"):
            path = f"meetings/transcripts/{self.transcript_id}{ext}"
            if self.cache.file_exists(path):
                self.transcript_text = self.cache.read_file(path)
                self.log.info(f"Loaded transcript: {self.transcript_id} ({len(self.transcript_text)} chars)")
                return

        raise ValueError(f"Transcript '{self.transcript_id}' not found in knowledge cache.")

    def collect_context(self) -> None:
        text = self.transcript_text.lower()

        # Find mentioned issue numbers
        issue_nums = set(int(m) for m in re.findall(r'#(\d+)', text))
        related_issues = []
        for num in issue_nums:
            path = f"github/issues/{num}.json"
            if self.cache.file_exists(path):
                issue = self.cache.read_json(path)
                related_issues.append({"number": num, "title": issue.get("title", "")})
        self.log.info(f"Found {len(related_issues)} mentioned issues")

        # Find mentioned PR numbers (pr #N or pull #N patterns)
        pr_nums = set(int(m) for m in re.findall(r'(?:pr|pull)\s*#?(\d+)', text))
        related_prs = []
        for num in pr_nums:
            path = f"github/pull_requests/{num}.json"
            if self.cache.file_exists(path):
                pr = self.cache.read_json(path)
                related_prs.append({"number": num, "title": pr.get("title", "")})
        self.log.info(f"Found {len(related_prs)} mentioned PRs")

        # Find mentioned Jira tickets
        jira_keys = set(re.findall(r'[A-Z]{2,}-\d+', self.transcript_text))
        related_jira = []
        for key in jira_keys:
            path = f"jira/tickets/{key}.json"
            if self.cache.file_exists(path):
                ticket = self.cache.read_json(path)
                related_jira.append({"key": key, "summary": ticket.get("summary", "")})
        self.log.info(f"Found {len(related_jira)} mentioned Jira tickets")

        self.context = {"related_issues": related_issues, "related_prs": related_prs, "related_jira": related_jira}

    def analyze(self) -> None:
        if not self.llm:
            raise RuntimeError("LLM client not configured")
        prompt_template = PROMPT_PATH.read_text()
        prompt = prompt_template.format(
            transcript=self.transcript_text[:15000],  # Limit transcript size
            related_issues=json.dumps(self.context["related_issues"], indent=2) if self.context["related_issues"] else "None found",
            related_prs=json.dumps(self.context["related_prs"], indent=2) if self.context["related_prs"] else "None found",
            jira_tickets=json.dumps(self.context["related_jira"], indent=2) if self.context["related_jira"] else "None found",
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
            self.analysis = {"title": self.transcript_id, "attendees": [], "summary": "Parse failure", "action_items": [], "decisions": [], "mentioned_issues": [], "mentioned_prs": [], "mentioned_jira_tickets": [], "key_topics": [], "confidence": 0.0}

        self.log.info(f"Analysis complete: {len(self.analysis.get('action_items', []))} action items, {len(self.analysis.get('decisions', []))} decisions")

    def generate_output(self) -> AgentOutput:
        output_data = {
            "meeting_id": self.transcript_id, **self.analysis, "llm_usage": self.llm_usage,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        return AgentOutput(
            status="success", summary=self.analysis.get("summary", f"Meeting {self.transcript_id} summarized"), data=output_data,
            artifacts=[
                {"type": "meeting_summary_json", "path": f"agent_outputs/meeting_summaries/{self.transcript_id}.json"},
                {"type": "meeting_summary_report", "path": f"agent_outputs/meeting_summaries/{self.transcript_id}.md"},
            ],
        )

    def store_artifacts(self, output: AgentOutput) -> list[str]:
        mid = self.transcript_id
        uris = []
        json_path = f"agent_outputs/meeting_summaries/{mid}.json"
        self.cache.write_json(json_path, output.data)
        uris.append(json_path)
        md_path = f"agent_outputs/meeting_summaries/{mid}.md"
        self.cache.write_file(md_path, self._generate_report(output.data))
        uris.append(md_path)
        self.log.info(f"Stored artifacts: {json_path}, {md_path}")
        return uris

    def _generate_report(self, data: dict) -> str:
        lines = [
            f"# Meeting Summary: {data.get('title', self.transcript_id)}",
            "", f"**Generated by:** meeting-summary agent", f"**Date:** {data.get('generated_at', 'N/A')}",
            f"**Confidence:** {data.get('confidence', 0)}",
        ]
        if data.get("attendees"):
            lines.extend(["", f"**Attendees:** {', '.join(data['attendees'])}"])
        lines.extend(["", "## Summary", data.get("summary", "N/A")])
        if data.get("action_items"):
            lines.extend(["", "## Action Items"])
            for item in data["action_items"]:
                assignee = item.get("assignee", "Unassigned")
                action = item.get("action", "")
                due = f" (due: {item['due']})" if item.get("due") else ""
                ref = ""
                if item.get("related_issue"):
                    ref = f" [#{item['related_issue']}]"
                elif item.get("related_jira"):
                    ref = f" [{item['related_jira']}]"
                lines.append(f"- **{assignee}:** {action}{ref}{due}")
        if data.get("decisions"):
            lines.extend(["", "## Decisions"] + [f"- {d}" for d in data["decisions"]])
        if data.get("key_topics"):
            lines.extend(["", "## Key Topics"] + [f"- {t}" for t in data["key_topics"]])
        refs = []
        if data.get("mentioned_issues"):
            refs.extend([f"#{n}" for n in data["mentioned_issues"]])
        if data.get("mentioned_prs"):
            refs.extend([f"PR #{n}" for n in data["mentioned_prs"]])
        if data.get("mentioned_jira_tickets"):
            refs.extend(data["mentioned_jira_tickets"])
        if refs:
            lines.extend(["", "## References", ", ".join(refs)])
        lines.extend(["", "---", f"*Job ID: {self.input.job_id if self.input else 'N/A'}*", ""])
        return "\n".join(lines)
