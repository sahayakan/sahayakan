"""Knowledge browsing API endpoints."""

import json
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.config import settings
from app.database import get_pool

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


def _cache_path() -> Path:
    return Path(settings.knowledge_cache_path)


@router.get("/issues")
async def list_issues():
    issues_dir = _cache_path() / "github" / "issues"
    if not issues_dir.exists():
        return {"issues": []}
    results = []
    for f in sorted(issues_dir.glob("*.json")):
        try:
            data = json.loads(f.read_text())
            results.append(
                {
                    "number": data.get("number", f.stem),
                    "title": data.get("title", ""),
                    "state": data.get("state", ""),
                    "labels": data.get("labels", []),
                    "created_at": data.get("created_at", ""),
                }
            )
        except Exception:
            results.append({"number": f.stem, "title": "Error reading file"})
    return {"issues": results}


@router.get("/issues/{number}")
async def get_issue(number: int):
    issue_file = _cache_path() / "github" / "issues" / f"{number}.json"
    if not issue_file.exists():
        raise HTTPException(status_code=404, detail=f"Issue #{number} not found in cache")
    return json.loads(issue_file.read_text())


@router.get("/pull-requests")
async def list_pull_requests():
    prs_dir = _cache_path() / "github" / "pull_requests"
    if not prs_dir.exists():
        return {"pull_requests": []}
    results = []
    for f in sorted(prs_dir.glob("*.json")):
        try:
            data = json.loads(f.read_text())
            results.append(
                {
                    "number": data.get("number", f.stem),
                    "title": data.get("title", ""),
                    "state": data.get("state", ""),
                    "merged": data.get("merged", False),
                    "created_at": data.get("created_at", ""),
                }
            )
        except Exception:
            results.append({"number": f.stem, "title": "Error reading file"})
    return {"pull_requests": results}


@router.get("/jira-tickets")
async def list_jira_tickets():
    tickets_dir = _cache_path() / "jira" / "tickets"
    if not tickets_dir.exists():
        return {"tickets": []}
    results = []
    for f in sorted(tickets_dir.glob("*.json")):
        try:
            data = json.loads(f.read_text())
            results.append(
                {
                    "key": data.get("key", f.stem),
                    "summary": data.get("summary", ""),
                    "status": data.get("status", ""),
                    "priority": data.get("priority", ""),
                }
            )
        except Exception:
            results.append({"key": f.stem, "summary": "Error reading file"})
    return {"tickets": results}


@router.get("/reports")
async def list_reports(report_type: str | None = None):
    outputs_dir = _cache_path() / "agent_outputs"
    if not outputs_dir.exists():
        return {"reports": []}
    reports = []
    for type_dir in sorted(outputs_dir.iterdir()):
        if not type_dir.is_dir():
            continue
        if report_type and type_dir.name != report_type:
            continue
        for f in sorted(type_dir.glob("*.md")):
            reports.append(
                {
                    "type": type_dir.name,
                    "id": f.stem,
                    "path": f"{type_dir.name}/{f.stem}",
                }
            )
    return {"reports": reports}


@router.get("/reports/{report_type}/{report_id}")
async def get_report(report_type: str, report_id: str):
    # Try markdown first, then JSON
    md_file = _cache_path() / "agent_outputs" / report_type / f"{report_id}.md"
    json_file = _cache_path() / "agent_outputs" / report_type / f"{report_id}.json"

    result = {}
    if md_file.exists():
        result["markdown"] = md_file.read_text()
    if json_file.exists():
        result["data"] = json.loads(json_file.read_text())

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Report {report_type}/{report_id} not found",
        )

    result["type"] = report_type
    result["id"] = report_id
    return result


@router.get("/meetings/transcripts")
async def list_transcripts():
    transcripts_dir = _cache_path() / "meetings" / "transcripts"
    if not transcripts_dir.exists():
        return {"transcripts": []}
    results = []
    for f in sorted(transcripts_dir.iterdir()):
        if f.is_file() and f.name != ".gitkeep":
            results.append({"id": f.stem, "filename": f.name, "size": f.stat().st_size})
    return {"transcripts": results}


@router.post("/meetings/transcripts", status_code=201)
async def upload_transcript(
    transcript_id: Annotated[str, Form(...)],
    file: Annotated[UploadFile, File(...)],
):
    transcripts_dir = _cache_path() / "meetings" / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)

    content = await file.read()
    text = content.decode("utf-8")

    ext = Path(file.filename).suffix if file.filename else ".txt"
    filepath = transcripts_dir / f"{transcript_id}{ext}"
    filepath.write_text(text)

    # Publish meeting.uploaded event
    try:
        pool = await get_pool()
        await pool.execute(
            "INSERT INTO events (event_type, source, payload) VALUES ('meeting.uploaded', 'api', $1::jsonb)",
            json.dumps({"transcript_id": transcript_id}),
        )
    except Exception:
        pass  # Event publishing is best-effort

    return {"transcript_id": transcript_id, "filename": filepath.name, "size": len(text)}
