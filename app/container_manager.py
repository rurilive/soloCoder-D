import asyncio
import json
import re
import subprocess
import uuid
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging

from app.database import db_manager, ContainerSession, InstalledPackage

logger = logging.getLogger(__name__)

CONTAINER_PREFIX = "sandbox-exec-"
DOCKER_IMAGE = "debian:bookworm-slim"
MAX_EXECUTION_TIME = 300
MAX_CONTAINERS = 10
MEMORY_LIMIT = "256m"
CPU_LIMIT = 0.5
MAX_PACKAGE_INSTALL_TIME = 120


@dataclass
class ExecutionResult:
    session_id: str
    output: str
    error: str
    exit_code: int
    is_running: bool


@dataclass
class ContainerStats:
    cpu_usage: float
    memory_usage: int
    memory_limit: int
    memory_percentage: float
    network_rx: int
    network_tx: int
    block_read: int
    block_write: int
    pids: int


@dataclass
class ContainerDetails:
    session_id: str
    container_id: str
    container_name: str
    image: str
    status: str
    created_at: datetime
    language: str
    ports: List[str] = field(default_factory=list)
    mounts: List[Dict] = field(default_factory=list)
    config: Dict = field(default_factory=dict)


@dataclass
class PackageInstallResult:
    session_id: str
    package_name: str
    version: str
    success: bool
    output: str
    error: str


@dataclass
class PackageListResult:
    session_id: str
    packages: List[Dict[str, str]]


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
            try:
                if dockerfile_path.exists():
                    dockerfile_path.unlink()
            except Exception:
                pass
            try:
                import shutil
                if temp_dir.exists():
                    shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass

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
            try:
                if dockerfile_path.exists():
                    dockerfile_path.unlink()
            except Exception:
                pass
            try:
                import shutil
                if temp_dir.exists():
                    shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass

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
            r"(?:wget\s+|curl\s+).*?(?:bash|sh)\s",
            r"(?:\|\s*bash|\|\s*sh)\b",
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
        
        sandbox_dir = Path(f"/tmp/sandbox-{session_id[:8]}")
        sandbox_dir.mkdir(exist_ok=True)

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
        try:
            result = await asyncio.create_subprocess_exec(
                "docker", "ps", "-a",
                "--filter", f"name={CONTAINER_PREFIX}",
                "--format", "{{.ID}}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                logger.warning(f"Docker command failed: {stderr.decode()}")
                return 0
            
            container_ids = stdout.decode().strip().split("\n")
            container_ids = [c for c in container_ids if c]
            
            cleaned = 0
            for container_id in container_ids:
                try:
                    await self._stop_container(container_id)
                    cleaned += 1
                except Exception as e:
                    logger.warning(f"Failed to cleanup container {container_id}: {e}")
            
            if cleaned > 0:
                logger.info(f"Cleaned up {cleaned} orphaned containers")
            return cleaned
        except FileNotFoundError:
            logger.warning("Docker command not found. Please ensure Docker is installed and in PATH.")
            return 0
        except Exception as e:
            logger.warning(f"Failed to cleanup orphaned containers: {e}")
            return 0

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

    async def get_container_details(self, session_id: str) -> ContainerDetails:
        session = await db_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        try:
            result = await asyncio.create_subprocess_exec(
                "docker", "inspect", session.container_id,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()

            if result.returncode != 0:
                raise Exception(f"Failed to inspect container: {stderr.decode()}")

            data = json.loads(stdout.decode())[0]

            container_name = data.get("Name", "").lstrip("/")
            image = data.get("Config", {}).get("Image", "")
            status = data.get("State", {}).get("Status", "")
            created_at = datetime.fromisoformat(data.get("Created", "").replace("Z", "+00:00"))

            ports = []
            port_data = data.get("NetworkSettings", {}).get("Ports", {})
            for port, bindings in (port_data or {}).items():
                if bindings:
                    for binding in bindings:
                        ports.append(f"{binding.get('HostIP', '')}:{binding.get('HostPort', '')}->{port}")

            mounts = []
            mount_data = data.get("Mounts", [])
            for mount in mount_data:
                mounts.append({
                    "source": mount.get("Source"),
                    "destination": mount.get("Destination"),
                    "type": mount.get("Type"),
                    "mode": mount.get("Mode")
                })

            config = {
                "memory": data.get("HostConfig", {}).get("Memory", 0),
                "cpus": data.get("HostConfig", {}).get("NanoCpus", 0) / 1e9 if data.get("HostConfig", {}).get("NanoCpus") else 0,
                "network_mode": data.get("HostConfig", {}).get("NetworkMode"),
                "capabilities": {
                    "drop": data.get("HostConfig", {}).get("CapDrop", [])
                }
            }

            return ContainerDetails(
                session_id=session_id,
                container_id=session.container_id,
                container_name=container_name,
                image=image,
                status=status,
                created_at=created_at,
                language=session.language,
                ports=ports,
                mounts=mounts,
                config=config
            )

        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse container info: {e}")

    async def get_container_stats(self, session_id: str) -> ContainerStats:
        session = await db_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        try:
            result = await asyncio.create_subprocess_exec(
                "docker", "stats", "--no-stream", "--format", "{{json .}}", session.container_id,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()

            if result.returncode != 0:
                raise Exception(f"Failed to get container stats: {stderr.decode()}")

            output = stdout.decode().strip()
            if not output:
                raise Exception("No stats data returned")

            data = json.loads(output)

            def parse_memory(mem_str: str) -> int:
                units = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}
                match = re.match(r"([\d.]+)\s*([A-Za-z]+)?", mem_str)
                if match:
                    num = float(match.group(1))
                    unit = match.group(2) or "B"
                    return int(num * units.get(unit, 1))
                return 0

            cpu_usage_str = data.get("CPUPerc", "0%")
            cpu_usage = float(cpu_usage_str.replace("%", "")) if cpu_usage_str else 0.0

            mem_usage_str = data.get("MemUsage", "0B / 0B")
            mem_parts = mem_usage_str.split(" / ")
            memory_usage = parse_memory(mem_parts[0]) if len(mem_parts) > 0 else 0
            memory_limit = parse_memory(mem_parts[1]) if len(mem_parts) > 1 else 0

            mem_perc_str = data.get("MemPerc", "0%")
            memory_percentage = float(mem_perc_str.replace("%", "")) if mem_perc_str else 0.0

            net_io_str = data.get("NetIO", "0B / 0B")
            net_parts = net_io_str.split(" / ")
            network_rx = parse_memory(net_parts[0]) if len(net_parts) > 0 else 0
            network_tx = parse_memory(net_parts[1]) if len(net_parts) > 1 else 0

            block_io_str = data.get("BlockIO", "0B / 0B")
            block_parts = block_io_str.split(" / ")
            block_read = parse_memory(block_parts[0]) if len(block_parts) > 0 else 0
            block_write = parse_memory(block_parts[1]) if len(block_parts) > 1 else 0

            pids_str = data.get("PIDs", "0")
            pids = int(pids_str) if pids_str.isdigit() else 0

            return ContainerStats(
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                memory_limit=memory_limit,
                memory_percentage=memory_percentage,
                network_rx=network_rx,
                network_tx=network_tx,
                block_read=block_read,
                block_write=block_write,
                pids=pids
            )

        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse stats data: {e}")

    async def pause_session(self, session_id: str) -> None:
        session = await db_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if session.status != "running":
            raise ValueError(f"Session {session_id} is not running")

        try:
            result = await asyncio.create_subprocess_exec(
                "docker", "pause", session.container_id,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()

            if result.returncode != 0:
                raise Exception(f"Failed to pause container: {stderr.decode()}")

            await db_manager.update_session_status(session_id, "paused")
            logger.info(f"Session {session_id} paused")

        except Exception as e:
            logger.error(f"Failed to pause session {session_id}: {e}")
            raise

    async def resume_session(self, session_id: str) -> None:
        session = await db_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if session.status != "paused":
            raise ValueError(f"Session {session_id} is not paused")

        try:
            result = await asyncio.create_subprocess_exec(
                "docker", "unpause", session.container_id,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()

            if result.returncode != 0:
                raise Exception(f"Failed to resume container: {stderr.decode()}")

            await db_manager.update_session_status(session_id, "running")
            logger.info(f"Session {session_id} resumed")

        except Exception as e:
            logger.error(f"Failed to resume session {session_id}: {e}")
            raise

    async def restart_session(self, session_id: str) -> None:
        session = await db_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        try:
            result = await asyncio.create_subprocess_exec(
                "docker", "restart", "-t", "2", session.container_id,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()

            if result.returncode != 0:
                raise Exception(f"Failed to restart container: {stderr.decode()}")

            await db_manager.update_session_status(session_id, "running")
            logger.info(f"Session {session_id} restarted")

        except Exception as e:
            logger.error(f"Failed to restart session {session_id}: {e}")
            raise

    async def get_container_logs(
        self,
        session_id: str,
        tail: int = 100,
        timestamps: bool = False
    ) -> str:
        session = await db_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        cmd = ["docker", "logs", "--tail", str(tail)]
        if timestamps:
            cmd.append("-t")
        cmd.append(session.container_id)

        try:
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
            stdout, _ = await result.communicate()

            return stdout.decode('utf-8', errors='replace')

        except Exception as e:
            logger.error(f"Failed to get logs for session {session_id}: {e}")
            raise

    async def install_package(
        self,
        session_id: str,
        package_name: str,
        version: Optional[str] = None,
        timeout: int = MAX_PACKAGE_INSTALL_TIME
    ) -> PackageInstallResult:
        session = await db_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if session.language != "python":
            raise ValueError(f"Package installation is only supported for Python sessions")

        if session.status not in ["running", "paused"]:
            raise ValueError(f"Session {session_id} is not active")

        lock = self._session_locks.get(session_id)
        if not lock:
            lock = asyncio.Lock()
            self._session_locks[session_id] = lock

        async with lock:
            if version:
                full_package = f"{package_name}=={version}"
            else:
                full_package = package_name

            cmd = [
                "docker", "exec", session.container_id,
                "pip3", "install", "--quiet", "--no-cache-dir", full_package
            ]

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
                    return PackageInstallResult(
                        session_id=session_id,
                        package_name=package_name,
                        version=version or "",
                        success=False,
                        output="",
                        error=f"Package installation timed out after {timeout} seconds"
                    )

                output = stdout.decode('utf-8', errors='replace')
                error = stderr.decode('utf-8', errors='replace')
                success = exit_code == 0

                if success:
                    installed_version = await self._get_installed_version(session.container_id, package_name)
                    await db_manager.add_installed_package(session_id, package_name, installed_version)
                    await db_manager.update_session_activity(session_id)

                    return PackageInstallResult(
                        session_id=session_id,
                        package_name=package_name,
                        version=installed_version,
                        success=True,
                        output=output,
                        error=error
                    )
                else:
                    return PackageInstallResult(
                        session_id=session_id,
                        package_name=package_name,
                        version=version or "",
                        success=False,
                        output=output,
                        error=error
                    )

            except Exception as e:
                return PackageInstallResult(
                    session_id=session_id,
                    package_name=package_name,
                    version=version or "",
                    success=False,
                    output="",
                    error=str(e)
                )

    async def _get_installed_version(self, container_id: str, package_name: str) -> str:
        try:
            result = await asyncio.create_subprocess_exec(
                "docker", "exec", container_id,
                "pip3", "show", package_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()

            if result.returncode == 0:
                output = stdout.decode('utf-8')
                for line in output.split('\n'):
                    if line.startswith('Version:'):
                        return line.split(':', 1)[1].strip()
            return ""
        except Exception:
            return ""

    async def list_installed_packages(self, session_id: str, refresh: bool = False) -> PackageListResult:
        session = await db_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if session.language != "python":
            raise ValueError(f"Package listing is only supported for Python sessions")

        if not refresh:
            db_packages = await db_manager.get_installed_packages(session_id)
            if db_packages:
                packages = [{"name": pkg.name, "version": pkg.version} for pkg in db_packages]
                return PackageListResult(session_id=session_id, packages=packages)

        try:
            result = await asyncio.create_subprocess_exec(
                "docker", "exec", session.container_id,
                "pip3", "list", "--format=freeze",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()

            if result.returncode != 0:
                raise Exception(f"Failed to list packages: {stderr.decode()}")

            output = stdout.decode('utf-8', errors='replace')
            packages = []

            for line in output.strip().split('\n'):
                if line and '==' in line:
                    name, version = line.split('==', 1)
                    packages.append({"name": name, "version": version})
                    await db_manager.add_installed_package(session_id, name, version)

            await db_manager.update_session_activity(session_id)

            return PackageListResult(session_id=session_id, packages=packages)

        except Exception as e:
            logger.error(f"Failed to list packages for session {session_id}: {e}")
            raise

    async def uninstall_package(
        self,
        session_id: str,
        package_name: str,
        timeout: int = 60
    ) -> PackageInstallResult:
        session = await db_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if session.language != "python":
            raise ValueError(f"Package uninstallation is only supported for Python sessions")

        if session.status not in ["running", "paused"]:
            raise ValueError(f"Session {session_id} is not active")

        lock = self._session_locks.get(session_id)
        if not lock:
            lock = asyncio.Lock()
            self._session_locks[session_id] = lock

        async with lock:
            cmd = [
                "docker", "exec", session.container_id,
                "pip3", "uninstall", "-y", "--quiet", package_name
            ]

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
                    return PackageInstallResult(
                        session_id=session_id,
                        package_name=package_name,
                        version="",
                        success=False,
                        output="",
                        error=f"Package uninstallation timed out after {timeout} seconds"
                    )

                output = stdout.decode('utf-8', errors='replace')
                error = stderr.decode('utf-8', errors='replace')
                success = exit_code == 0

                if success:
                    await db_manager.remove_installed_package(session_id, package_name)
                    await db_manager.update_session_activity(session_id)

                return PackageInstallResult(
                    session_id=session_id,
                    package_name=package_name,
                    version="",
                    success=success,
                    output=output,
                    error=error
                )

            except Exception as e:
                return PackageInstallResult(
                    session_id=session_id,
                    package_name=package_name,
                    version="",
                    success=False,
                    output="",
                    error=str(e)
                )


container_manager = ContainerManager()
