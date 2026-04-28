import asyncio
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.websockets import WebSocket, WebSocketDisconnect

from app.database import db_manager
from app.container_manager import container_manager, ExecutionResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"
TEMPLATES_DIR = Path(__file__).parent / "templates"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db_manager.init_db()
    await container_manager.cleanup_orphaned_containers()
    logger.info("Application initialized successfully")
    yield
    logger.info("Cleaning up all sessions...")
    await container_manager.stop_all_sessions()
    await db_manager.clear_all_sessions()
    logger.info("All sessions cleaned up")


app = FastAPI(
    title="Sandbox Executor",
    description="Secure code execution sandbox using Docker",
    version="0.1.0",
    lifespan=lifespan
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


class CodeExecutionRequest(BaseModel):
    code: str
    session_id: Optional[str] = None
    language: str = "python"


class SessionCreateRequest(BaseModel):
    language: str = "python"


class SessionStopRequest(BaseModel):
    session_id: str





@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/sessions")
async def list_sessions():
    sessions = await container_manager.get_all_sessions_info()
    return {"sessions": sessions}


@app.post("/api/sessions")
async def create_session(request: SessionCreateRequest):
    try:
        session_id = await container_manager.create_session(request.language)
        return {
            "session_id": session_id,
            "language": request.language,
            "status": "created"
        }
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/sessions/{session_id}")
async def stop_session(session_id: str):
    try:
        await container_manager.stop_session(session_id)
        return {"status": "stopped", "session_id": session_id}
    except Exception as e:
        logger.error(f"Failed to stop session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/execute")
async def execute_code(request: CodeExecutionRequest):
    if not request.session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    
    try:
        result = await container_manager.execute_code(
            session_id=request.session_id,
            code=request.code
        )
        return {
            "session_id": result.session_id,
            "output": result.output,
            "error": result.error,
            "exit_code": result.exit_code,
            "is_running": result.is_running
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to execute code: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/clear-all")
async def clear_all_sessions(background_tasks: BackgroundTasks):
    try:
        background_tasks.add_task(container_manager.stop_all_sessions)
        return {"status": "clearing", "message": "All sessions are being cleared in background"}
    except Exception as e:
        logger.error(f"Failed to clear sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status/{session_id}")
async def get_session_status(session_id: str):
    try:
        is_running = await container_manager.is_session_running(session_id)
        return {
            "session_id": session_id,
            "is_running": is_running
        }
    except Exception as e:
        logger.error(f"Failed to get session status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/execute/{session_id}")
async def websocket_execute(websocket: WebSocket, session_id: str):
    await websocket.accept()
    
    try:
        is_running = await container_manager.is_session_running(session_id)
        if not is_running:
            await websocket.send_json({
                "type": "error",
                "message": f"Session {session_id} is not running"
            })
            await websocket.close()
            return
        
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id
        })
        
        while True:
            try:
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                    if isinstance(message, dict) and message.get("type") == "execute":
                        code = message.get("code", "")
                        
                        result = await container_manager.execute_code(
                            session_id=session_id,
                            code=code
                        )
                        
                        await websocket.send_json({
                            "type": "result",
                            "output": result.output,
                            "error": result.error,
                            "exit_code": result.exit_code
                        })
                except Exception:
                    pass
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })
                except:
                    break
                    
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    finally:
        try:
            await websocket.close()
        except:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=4444,
        reload=True
    )
