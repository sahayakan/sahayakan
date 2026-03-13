from fastapi import APIRouter, HTTPException

from app.database import get_pool
from app.models.jira_projects import JiraProjectCreate, JiraProjectResponse, JiraProjectUpdate

router = APIRouter(prefix="/jira-projects", tags=["jira-projects"])

COLUMNS = "id, name, project_key, base_url, is_active, created_at, updated_at"


@router.get("", response_model=list[JiraProjectResponse])
async def list_jira_projects():
    pool = await get_pool()
    rows = await pool.fetch(f"SELECT {COLUMNS} FROM jira_projects ORDER BY created_at DESC")
    return [dict(row) for row in rows]


@router.get("/{project_id}", response_model=JiraProjectResponse)
async def get_jira_project(project_id: int):
    pool = await get_pool()
    row = await pool.fetchrow(f"SELECT {COLUMNS} FROM jira_projects WHERE id = $1", project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Jira project not found")
    return dict(row)


@router.post("", response_model=JiraProjectResponse, status_code=201)
async def create_jira_project(project: JiraProjectCreate):
    pool = await get_pool()
    try:
        row = await pool.fetchrow(
            f"INSERT INTO jira_projects (name, project_key, base_url) VALUES ($1, $2, $3) RETURNING {COLUMNS}",
            project.name,
            project.project_key,
            project.base_url,
        )
    except Exception as e:
        if "unique" in str(e).lower():
            raise HTTPException(
                status_code=409,
                detail=f"Jira project '{project.name}' or key '{project.project_key}' already exists",
            ) from e
        raise
    return dict(row)


@router.put("/{project_id}", response_model=JiraProjectResponse)
async def update_jira_project(project_id: int, project: JiraProjectUpdate):
    pool = await get_pool()
    existing = await pool.fetchrow("SELECT id FROM jira_projects WHERE id = $1", project_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Jira project not found")

    updates = {k: v for k, v in project.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clauses = [f"{k} = ${i + 1}" for i, k in enumerate(updates)]
    set_clauses.append("updated_at = NOW()")
    values = list(updates.values())
    values.append(project_id)

    row = await pool.fetchrow(
        f"UPDATE jira_projects SET {', '.join(set_clauses)} WHERE id = ${len(values)} RETURNING {COLUMNS}",
        *values,
    )
    return dict(row)


@router.delete("/{project_id}", status_code=204)
async def delete_jira_project(project_id: int):
    pool = await get_pool()
    result = await pool.execute("DELETE FROM jira_projects WHERE id = $1", project_id)
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Jira project not found")
