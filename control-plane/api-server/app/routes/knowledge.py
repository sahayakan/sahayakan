from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.config import settings

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/issues")
async def list_issues():
    """List ingested issues. Full implementation in Stage 3."""
    issues_dir = Path(settings.knowledge_cache_path) / "github" / "issues"
    if not issues_dir.exists():
        return {"issues": []}
    files = sorted(issues_dir.glob("*.json"))
    return {"issues": [f.stem for f in files]}


@router.get("/reports")
async def list_reports():
    """List generated reports. Full implementation in Stage 3."""
    outputs_dir = Path(settings.knowledge_cache_path) / "agent_outputs"
    if not outputs_dir.exists():
        return {"reports": []}
    reports = []
    for report_type_dir in sorted(outputs_dir.iterdir()):
        if report_type_dir.is_dir():
            for f in sorted(report_type_dir.glob("*.md")):
                reports.append(
                    {"type": report_type_dir.name, "id": f.stem}
                )
    return {"reports": reports}
