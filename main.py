import asyncio
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse
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
    image_tag: Optional[str] = None


class SessionStopRequest(BaseModel):
    session_id: str


class PackageInstallRequest(BaseModel):
    package_name: str
    version: Optional[str] = None


class PackageListRequest(BaseModel):
    refresh: bool = False





@app.get("/")
async def index(request: Request):
    html_content = (TEMPLATES_DIR / "index.html").read_text()
    return HTMLResponse(content=html_content)


@app.get("/api/sessions")
async def list_sessions():
    sessions = await container_manager.get_all_sessions_info()
    return {"sessions": sessions}


@app.post("/api/sessions")
async def create_session(data: SessionCreateRequest):
    try:
        session_id = await container_manager.create_session(data.language, data.image_tag)
        return {
            "session_id": session_id,
            "language": data.language,
            "image_tag": data.image_tag,
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
async def execute_code(data: CodeExecutionRequest):
    if not data.session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    
    try:
        result = await container_manager.execute_code(
            session_id=data.session_id,
            code=data.code
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


@app.get("/api/sessions/{session_id}/details")
async def get_session_details(session_id: str):
    try:
        details = await container_manager.get_container_details(session_id)
        return {
            "session_id": details.session_id,
            "container_id": details.container_id,
            "container_name": details.container_name,
            "image": details.image,
            "status": details.status,
            "created_at": details.created_at.isoformat(),
            "language": details.language,
            "ports": details.ports,
            "mounts": details.mounts,
            "config": details.config
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get session details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions/{session_id}/stats")
async def get_session_stats(session_id: str):
    try:
        stats = await container_manager.get_container_stats(session_id)
        return {
            "session_id": session_id,
            "cpu_usage": stats.cpu_usage,
            "memory_usage": stats.memory_usage,
            "memory_limit": stats.memory_limit,
            "memory_percentage": stats.memory_percentage,
            "network_rx": stats.network_rx,
            "network_tx": stats.network_tx,
            "block_read": stats.block_read,
            "block_write": stats.block_write,
            "pids": stats.pids
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get session stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sessions/{session_id}/pause")
async def pause_session(session_id: str):
    try:
        await container_manager.pause_session(session_id)
        return {"status": "paused", "session_id": session_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to pause session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sessions/{session_id}/resume")
async def resume_session(session_id: str):
    try:
        await container_manager.resume_session(session_id)
        return {"status": "running", "session_id": session_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to resume session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sessions/{session_id}/restart")
async def restart_session(session_id: str):
    try:
        await container_manager.restart_session(session_id)
        return {"status": "restarted", "session_id": session_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to restart session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions/{session_id}/logs")
async def get_session_logs(
    session_id: str,
    tail: int = 100,
    timestamps: bool = False
):
    try:
        logs = await container_manager.get_container_logs(
            session_id=session_id,
            tail=tail,
            timestamps=timestamps
        )
        return {
            "session_id": session_id,
            "logs": logs
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get session logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions/{session_id}/packages")
async def list_packages(
    session_id: str,
    refresh: bool = False
):
    try:
        result = await container_manager.list_installed_packages(
            session_id=session_id,
            refresh=refresh
        )
        return {
            "session_id": result.session_id,
            "packages": result.packages
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to list packages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sessions/{session_id}/packages")
async def install_package(session_id: str, data: PackageInstallRequest):
    try:
        result = await container_manager.install_package(
            session_id=session_id,
            package_name=data.package_name,
            version=data.version
        )
        return {
            "session_id": result.session_id,
            "package_name": result.package_name,
            "version": result.version,
            "success": result.success,
            "output": result.output,
            "error": result.error
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to install package: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/sessions/{session_id}/packages/{package_name}")
async def uninstall_package(session_id: str, package_name: str):
    try:
        result = await container_manager.uninstall_package(
            session_id=session_id,
            package_name=package_name
        )
        return {
            "session_id": result.session_id,
            "package_name": result.package_name,
            "success": result.success,
            "output": result.output,
            "error": result.error
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to uninstall package: {e}")
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
