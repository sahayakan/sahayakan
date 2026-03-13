"""WebSocket endpoint for real-time log streaming."""

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.log_store import get_logs, subscribe, unsubscribe

router = APIRouter()


@router.websocket("/ws/logs/{job_id}")
async def log_stream(websocket: WebSocket, job_id: int):
    await websocket.accept()

    # Send existing logs first
    existing = get_logs(job_id, offset=0, limit=1000)
    for entry in existing:
        await websocket.send_json(entry)

    # Subscribe for new logs
    queue = subscribe(job_id)
    try:
        while True:
            entry = await queue.get()
            await websocket.send_json(entry.to_dict())
    except WebSocketDisconnect:
        pass
    finally:
        unsubscribe(job_id, queue)
