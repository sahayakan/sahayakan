Scaffold a new API route module for Sahayakan. Resource name: "$ARGUMENTS"

Steps:

1. Create `control-plane/api-server/app/routes/{resource_name}.py` following the pattern in existing routes (e.g., `agents.py`):
   ```python
   from fastapi import APIRouter, HTTPException

   from app.database import get_pool

   router = APIRouter(prefix="/{resource_name}", tags=["{resource_name}"])


   @router.get("")
   async def list_{resource_name}():
       pool = await get_pool()
       # TODO: implement query
       return []
   ```

2. Update `control-plane/api-server/app/main.py`:
   - Add the import in the `from app.routes import ...` line
   - Add `app.include_router({resource_name}.router)` after the existing router registrations

3. Report what was created and remind the user to:
   - Define request/response models in `control-plane/api-server/app/models/` if needed
   - Implement the route handlers
   - Add any required database migrations
   - No Caddy changes needed — production uses `/api/*` prefix routing which covers all API routes automatically
