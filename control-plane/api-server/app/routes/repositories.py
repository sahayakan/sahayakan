from fastapi import APIRouter, HTTPException

from app.database import get_pool
from app.models.repositories import RepositoryCreate, RepositoryResponse, RepositoryUpdate

router = APIRouter(prefix="/repositories", tags=["repositories"])


@router.get("", response_model=list[RepositoryResponse])
async def list_repositories():
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT id, name, url, provider, default_branch, is_active, "
        "created_at, updated_at FROM repositories ORDER BY created_at DESC"
    )
    return [dict(row) for row in rows]


@router.get("/{repo_id}", response_model=RepositoryResponse)
async def get_repository(repo_id: int):
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT id, name, url, provider, default_branch, is_active, "
        "created_at, updated_at FROM repositories WHERE id = $1",
        repo_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Repository not found")
    return dict(row)


@router.post("", response_model=RepositoryResponse, status_code=201)
async def create_repository(repo: RepositoryCreate):
    pool = await get_pool()
    try:
        row = await pool.fetchrow(
            "INSERT INTO repositories (name, url, provider, default_branch) "
            "VALUES ($1, $2, $3, $4) "
            "RETURNING id, name, url, provider, default_branch, is_active, "
            "created_at, updated_at",
            repo.name,
            repo.url,
            repo.provider,
            repo.default_branch,
        )
    except Exception as e:
        if "unique" in str(e).lower():
            raise HTTPException(
                status_code=409,
                detail=f"Repository '{repo.name}' already exists",
            ) from e
        raise
    return dict(row)


@router.put("/{repo_id}", response_model=RepositoryResponse)
async def update_repository(repo_id: int, repo: RepositoryUpdate):
    pool = await get_pool()
    existing = await pool.fetchrow("SELECT id FROM repositories WHERE id = $1", repo_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Repository not found")

    updates = {k: v for k, v in repo.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clauses = [f"{k} = ${i + 1}" for i, k in enumerate(updates)]
    set_clauses.append(f"updated_at = NOW()")
    values = list(updates.values())
    values.append(repo_id)

    row = await pool.fetchrow(
        f"UPDATE repositories SET {', '.join(set_clauses)} "
        f"WHERE id = ${len(values)} "
        "RETURNING id, name, url, provider, default_branch, is_active, "
        "created_at, updated_at",
        *values,
    )
    return dict(row)


@router.delete("/{repo_id}", status_code=204)
async def delete_repository(repo_id: int):
    pool = await get_pool()
    result = await pool.execute("DELETE FROM repositories WHERE id = $1", repo_id)
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Repository not found")
