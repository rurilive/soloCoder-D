import asyncio
import json
import re
import subprocess
import uuid
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone
import logging

from app.database import db_manager, ContainerSession

logger = logging.getLogger(__name__)

CONTAINER_PREFIX = "sandbox-exec-"
DOCKER_IMAGE = "debian:bookworm-slim"
MAX_EXECUTION_TIME = 300
MAX_CONTAINERS = 10
MEMORY_LIMIT = "256m"
CPU_LIMIT = 0.5


@dataclass
class ExecutionResult:
    session_id: str
    output: str
    error: str
    exit_code: int
    is_running: bool


class ContainerManager:
    def __init__(self):
        self._session_locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    async def _ensure_python_image(self) -> str:
        image_name = "sandbox-python:latest"
        try:
            result = await asyncio.create_subprocess_exec(
                "docker", "inspect", image_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            if result.returncode == 0:
                return image_name
        except Exception:
            pass

        dockerfile_content = f"""FROM {DOCKER_IMAGE}
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /sandbox
CMD ["sleep", "infinity"]
"""
        temp_dir = Path("/tmp/sandbox-build-python")
        temp_dir.mkdir(exist_ok=True)
        dockerfile_path = temp_dir / "Dockerfile"
        dockerfile_path.write_text(dockerfile_content)

        try:
            result = await asyncio.create_subprocess_exec(
                "docker", "build", "-t", image_name, str(temp_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            if result.returncode != 0:
                logger.error(f"Failed to build Python image: {stderr.decode()}")
                raise Exception(f"Failed to build Python image: {stderr.decode()}")
            return image_name
        finally:
            dockerfile_path.unlink()
            temp_dir.rmdir()

    async def _ensure_nodejs_image(self) -> str:
        image_name = "sandbox-nodejs:latest"
        try:
            result = await asyncio.create_subprocess_exec(
                "docker", "inspect", image_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            if result.returncode == 0:
                return image_name
        except Exception:
            pass

        dockerfile_content = f"""FROM {DOCKER_IMAGE}
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /sandbox
CMD ["sleep", "infinity"]
"""
        temp_dir = Path("/tmp/sandbox-build-node")
        temp_dir.mkdir(exist_ok=True)
        dockerfile_path = temp_dir / "Dockerfile"
        dockerfile_path.write_text(dockerfile_content)

        try:
            result = await asyncio.create_subprocess_exec(
                "docker", "build", "-t", image_name, str(temp_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            if result.returncode != 0:
                logger.error(f"Failed to build Node.js image: {stderr.decode()}")
                raise Exception(f"Failed to build Node.js image: {stderr.decode()}")
            return image_name
        finally:
            dockerfile_path.unlink()
            temp_dir.rmdir()

    async def _get_image_for_language(self, language: str) -> str:
        if language == "python":
            return await self._ensure_python_image()
        elif language == "javascript":
            return await self._ensure_nodejs_image()
        else:
            raise ValueError(f"Unsupported language: {language}")

    def _sanitize_code(self, code: str, language: str) -> str:
        dangerous_patterns = [
            r"(?:sudo|su|doas)\s+",
            r"(?:rm\s+-rf|rm\s+(-r\s+|-f\s+)+--no-preserve-root)",
            r"(?:chmod\s+777|chmod\s+\+rwx)",
            r"(?:\bdd\b\s+if=|of=/dev)",
            r"(?:mkfs|fdisk|mount|umount)",
            r"(?:iptables|ip6tables|nftables)",
            r"(?:passwd|shadow)",
            r"(?:crontab|at\s+)",
            r"(?:wget\s+|curl\s+).*?bash|sh",
            r"(?:eval\s*\()|(?:exec\s*\()",
            r"(?:__import__|subprocess|os\.system|os\.popen)",
            r"(?:import\s+ctypes|from\s+ctypes)",
            r"(?:socket\.socket|import\s+socket)",
            r"(?:requests\.|urllib\.|http\.client)",
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                raise ValueError(f"Code contains potentially dangerous operations: pattern matched {pattern}")
        
        return code

    async def create_session(self, language: str) -> str:
        async with self._global_lock:
            sessions = await db_manager.get_all_sessions()
            running_sessions = [s for s in sessions if s.status == "running"]
            if len(running_sessions) >= MAX_CONTAINERS:
                raise Exception(f"Maximum number of containers ({MAX_CONTAINERS}) reached. Please stop some containers first.")

        image_name = await self._get_image_for_language(language)
        session_id = str(uuid.uuid4())
        container_name = f"{CONTAINER_PREFIX}{session_id[:8]}"

        container_id = None
        try:
            result = await asyncio.create_subprocess_exec(
                "docker", "run",
                "-d",
                "--name", container_name,
                "--network", "none",
                "--read-only",
                "--memory", MEMORY_LIMIT,
                "--cpus", str(CPU_LIMIT),
                "--ulimit", "nproc=128:128",
                "--ulimit", "nofile=256:256",
                "--cap-drop", "ALL",
                "--security-opt", "no-new-privileges",
                "--pids-limit", "64",
                "-v", f"/tmp/sandbox-{session_id[:8]}:/sandbox:rw",
                image_name,
                "sleep", "infinity",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                raise Exception(f"Failed to start container: {stderr.decode()}")
            
            container_id = stdout.decode().strip()
            
            sandbox_dir = Path(f"/tmp/sandbox-{session_id[:8]}")
            sandbox_dir.mkdir(exist_ok=True)
            
            session = ContainerSession(
                id=session_id,
                language=language,
                container_id=container_id,
                created_at=datetime.now(timezone.utc),
                status="running",
                last_active_at=datetime.now(timezone.utc)
            )
            
            await db_manager.create_session(session)
            self._session_locks[session_id] = asyncio.Lock()
            
            return session_id
            
        except Exception as e:
            if container_id:
                try:
                    await self._stop_container(container_id)
                except:
                    pass
            raise e

    async def _stop_container(self, container_id: str) -> None:
        result = await asyncio.create_subprocess_exec(
            "docker", "stop", "-t", "2", container_id,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await result.communicate()
        
        result = await asyncio.create_subprocess_exec(
            "docker", "rm", "-f", container_id,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await result.communicate()

    async def stop_session(self, session_id: str) -> None:
        session = await db_manager.get_session(session_id)
        if not session:
            return
        
        try:
            await self._stop_container(session.container_id)
        except Exception as e:
            logger.warning(f"Failed to stop container {session.container_id}: {e}")
        
        try:
            sandbox_dir = Path(f"/tmp/sandbox-{session_id[:8]}")
            if sandbox_dir.exists():
                import shutil
                shutil.rmtree(sandbox_dir, ignore_errors=True)
        except Exception as e:
            logger.warning(f"Failed to cleanup sandbox dir for {session_id}: {e}")
        
        await db_manager.update_session_status(session_id, "stopped")
        
        if session_id in self._session_locks:
            del self._session_locks[session_id]

    async def stop_all_sessions(self) -> None:
        sessions = await db_manager.get_all_sessions()
        for session in sessions:
            if session.status == "running":
                try:
                    await self.stop_session(session.id)
                except Exception as e:
                    logger.error(f"Failed to stop session {session.id}: {e}")

    async def cleanup_orphaned_containers(self) -> int:
        result = await asyncio.create_subprocess_exec(
            "docker", "ps", "-a",
            "--filter", f"name={CONTAINER_PREFIX}",
            "--format", "{{.ID}}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await result.communicate()
        
        container_ids = stdout.decode().strip().split("\n")
        container_ids = [c for c in container_ids if c]
        
        cleaned = 0
        for container_id in container_ids:
            try:
                await self._stop_container(container_id)
                cleaned += 1
            except Exception as e:
                logger.warning(f"Failed to cleanup container {container_id}: {e}")
        
        return cleaned

    async def execute_code(
        self,
        session_id: str,
        code: str,
        timeout: int = MAX_EXECUTION_TIME
    ) -> ExecutionResult:
        session = await db_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        if session.status != "running":
            raise ValueError(f"Session {session_id} is not running")
        
        try:
            code = self._sanitize_code(code, session.language)
        except ValueError as e:
            return ExecutionResult(
                session_id=session_id,
                output="",
                error=str(e),
                exit_code=1,
                is_running=True
            )
        
        lock = self._session_locks.get(session_id)
        if not lock:
            lock = asyncio.Lock()
            self._session_locks[session_id] = lock
        
        async with lock:
            sandbox_dir = Path(f"/tmp/sandbox-{session_id[:8]}")
            sandbox_dir.mkdir(exist_ok=True)
            
            if session.language == "python":
                file_name = "exec.py"
                file_path = sandbox_dir / file_name
                file_path.write_text(code)
                cmd = ["docker", "exec", session.container_id, "python3", "-u", f"/sandbox/{file_name}"]
            elif session.language == "javascript":
                file_name = "exec.js"
                file_path = sandbox_dir / file_name
                file_path.write_text(code)
                cmd = ["docker", "exec", session.container_id, "node", f"/sandbox/{file_name}"]
            else:
                raise ValueError(f"Unsupported language: {session.language}")
            
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                try:
                    stdout, stderr = await asyncio.wait_for(
                        proc.communicate(),
                        timeout=timeout
                    )
                    exit_code = proc.returncode
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()
                    return ExecutionResult(
                        session_id=session_id,
                        output="",
                        error=f"Execution timed out after {timeout} seconds",
                        exit_code=-1,
                        is_running=True
                    )
                
                await db_manager.update_session_activity(session_id)
                
                return ExecutionResult(
                    session_id=session_id,
                    output=stdout.decode('utf-8', errors='replace'),
                    error=stderr.decode('utf-8', errors='replace'),
                    exit_code=exit_code if exit_code is not None else -1,
                    is_running=True
                )
                
            except Exception as e:
                return ExecutionResult(
                    session_id=session_id,
                    output="",
                    error=str(e),
                    exit_code=-1,
                    is_running=True
                )

    async def is_session_running(self, session_id: str) -> bool:
        session = await db_manager.get_session(session_id)
        if not session:
            return False
        return session.status == "running"

    async def get_all_sessions_info(self) -> List[Dict]:
        sessions = await db_manager.get_all_sessions()
        result = []
        for session in sessions:
            result.append({
                "id": session.id,
                "language": session.language,
                "container_id": session.container_id,
                "created_at": session.created_at.isoformat(),
                "status": session.status,
                "last_active_at": session.last_active_at.isoformat()
            })
        return result


container_manager = ContainerManager()
