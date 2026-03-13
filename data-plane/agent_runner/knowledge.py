"""Knowledge cache library for reading, writing, and committing files."""

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path


class KnowledgeCache:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self._ensure_git_repo()

    def _ensure_git_repo(self) -> None:
        git_dir = self.base_path / ".git"
        if not git_dir.exists():
            subprocess.run(
                ["git", "init"],
                cwd=self.base_path,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "sahayakan@agent.local"],
                cwd=self.base_path,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Sahayakan Agent"],
                cwd=self.base_path,
                capture_output=True,
                check=True,
            )

    def read_file(self, relative_path: str) -> str:
        full_path = self.base_path / relative_path
        return full_path.read_text()

    def read_json(self, relative_path: str) -> dict:
        return json.loads(self.read_file(relative_path))

    def write_file(self, relative_path: str, content: str) -> Path:
        full_path = self.base_path / relative_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
        return full_path

    def write_json(self, relative_path: str, data: dict) -> Path:
        return self.write_file(relative_path, json.dumps(data, indent=2))

    def list_files(self, relative_dir: str, pattern: str = "*") -> list[str]:
        dir_path = self.base_path / relative_dir
        if not dir_path.exists():
            return []
        return [
            str(f.relative_to(self.base_path))
            for f in sorted(dir_path.glob(pattern))
            if f.is_file() and f.name != ".gitkeep"
        ]

    def file_exists(self, relative_path: str) -> bool:
        return (self.base_path / relative_path).exists()

    def commit(
        self,
        message: str,
        files: list[str],
        agent_name: str = "",
        job_id: int | None = None,
        source: str = "",
    ) -> str:
        """Commit files and return the commit hash."""
        for f in files:
            subprocess.run(
                ["git", "add", f],
                cwd=self.base_path,
                capture_output=True,
                check=True,
            )

        timestamp = datetime.now(UTC).isoformat()
        full_message = f"[AI-Agent] {agent_name}: {message}"
        if agent_name or job_id or source:
            full_message += "\n"
            if agent_name:
                full_message += f"\nAgent: {agent_name}"
            if job_id is not None:
                full_message += f"\nJob ID: {job_id}"
            if source:
                full_message += f"\nSource: {source}"
            full_message += f"\nTimestamp: {timestamp}"

        subprocess.run(
            ["git", "commit", "-m", full_message, "--allow-empty"],
            cwd=self.base_path,
            capture_output=True,
            text=True,
        )

        # Get commit hash
        hash_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.base_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return hash_result.stdout.strip()
