import asyncio
import hashlib
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
DEFAULT_PYTHON_IMAGE = "python:3.11-alpine3.22"
DEFAULT_NODE_IMAGE = "node:20-alpine"
DEFAULT_GO_IMAGE = "golang:1.22-alpine"
DEFAULT_C_IMAGE = "gcc:13"
DEFAULT_CPP_IMAGE = "gcc:13"
DEFAULT_JAVA_IMAGE = "eclipse-temurin:21-jdk"
DEFAULT_LUA_IMAGE = "lua:5.4-alpine"
MAX_EXECUTION_TIME = 300
MAX_CONTAINERS = 10
MEMORY_LIMIT = "256m"
CPU_LIMIT = 0.5
MAX_PACKAGE_INSTALL_TIME = 120
SITE_PACKAGES_DIR = "site-packages"
SITE_PACKAGES_MOUNT_PATH = "/site-packages"
JAVA_COMPILE_CACHE_DIR = "java_cache"
JAVA_COMPILE_CACHE_MAX_SIZE = 100

PYTHON_IMAGE_PREFIX = "python:"
NODE_IMAGE_PREFIX = "node:"
GO_IMAGE_PREFIX = "golang:"
C_IMAGE_PREFIX = "gcc:"
CPP_IMAGE_PREFIX = "gcc:"
JAVA_IMAGE_PREFIX = "eclipse-temurin:"
LUA_IMAGE_PREFIX = "lua:"


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
        self._java_compile_cache: Dict[str, Tuple[str, str, datetime]] = {}  # hash -> (file_name, class_name, timestamp)
        self._java_cache_lock = asyncio.Lock()

    def _get_image_name(self, language: str, image_tag: Optional[str] = None) -> str:
        if language == "python":
            if image_tag:
                if not re.match(r'^[\w.-]+$', image_tag):
                    raise ValueError(f"Invalid Python tag: {image_tag}")
                return f"{PYTHON_IMAGE_PREFIX}{image_tag}"
            return DEFAULT_PYTHON_IMAGE
        elif language == "javascript":
            if image_tag:
                if not re.match(r'^[\w.-]+$', image_tag):
                    raise ValueError(f"Invalid Node.js tag: {image_tag}")
                return f"{NODE_IMAGE_PREFIX}{image_tag}"
            return DEFAULT_NODE_IMAGE
        elif language == "go":
            if image_tag:
                if not re.match(r'^[\w.-]+$', image_tag):
                    raise ValueError(f"Invalid Go tag: {image_tag}")
                return f"{GO_IMAGE_PREFIX}{image_tag}"
            return DEFAULT_GO_IMAGE
        elif language == "c":
            if image_tag:
                if not re.match(r'^[\w.-]+$', image_tag):
                    raise ValueError(f"Invalid C tag: {image_tag}")
                return f"{C_IMAGE_PREFIX}{image_tag}"
            return DEFAULT_C_IMAGE
        elif language == "cpp" or language == "c++":
            if image_tag:
                if not re.match(r'^[\w.-]+$', image_tag):
                    raise ValueError(f"Invalid C++ tag: {image_tag}")
                return f"{CPP_IMAGE_PREFIX}{image_tag}"
            return DEFAULT_CPP_IMAGE
        elif language == "java":
            if image_tag:
                if not re.match(r'^[\w.-]+$', image_tag):
                    raise ValueError(f"Invalid Java tag: {image_tag}")
                return f"{JAVA_IMAGE_PREFIX}{image_tag}"
            return DEFAULT_JAVA_IMAGE
        elif language == "lua":
            if image_tag:
                if not re.match(r'^[\w.-]+$', image_tag):
                    raise ValueError(f"Invalid Lua tag: {image_tag}")
                return f"{LUA_IMAGE_PREFIX}{image_tag}"
            return DEFAULT_LUA_IMAGE
        else:
            raise ValueError(f"Unsupported language: {language}")

    async def _ensure_image(self, image_name: str) -> None:
        try:
            result = await asyncio.create_subprocess_exec(
                "docker", "inspect", image_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            if result.returncode == 0:
                return
        except Exception:
            pass

        logger.info(f"Pulling image: {image_name}")
        result = await asyncio.create_subprocess_exec(
            "docker", "pull", image_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await result.communicate()
        if result.returncode != 0:
            logger.error(f"Failed to pull image {image_name}: {stderr.decode()}")
            raise Exception(f"Failed to pull image {image_name}: {stderr.decode()}")

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

    def _prepare_java_code(self, code: str) -> Tuple[str, str]:
        class_pattern = r'(?:public\s+)?class\s+(\w+)'
        main_method_pattern = r'public\s+static\s+void\s+main\s*\(\s*String\s*\[\s*\]\s*\w+\s*\)'
        
        class_matches = list(re.finditer(class_pattern, code))
        main_method_match = re.search(main_method_pattern, code)
        
        class_names = [match.group(1) for match in class_matches]
        
        if main_method_match:
            main_class_start = main_method_match.start()
            for i, match in enumerate(class_matches):
                class_start = match.start()
                next_class_start = class_matches[i + 1].start() if i + 1 < len(class_matches) else len(code)
                
                if class_start <= main_class_start < next_class_start:
                    main_class_name = match.group(1)
                    file_name = f"{main_class_name}.java"
                    return file_name, code
        
        if "public class" in code:
            public_class_pattern = r'public\s+class\s+(\w+)'
            public_class_match = re.search(public_class_pattern, code)
            if public_class_match:
                class_name = public_class_match.group(1)
                file_name = f"{class_name}.java"
                return file_name, code
        
        if class_names:
            class_name = class_names[0]
            file_name = f"{class_name}.java"
            return file_name, code
        
        default_code = '''public class Main {
    public static void main(String[] args) {
''' + code + '''
    }
}'''
        return "Main.java", default_code

    def _compute_java_code_hash(self, code: str) -> str:
        return hashlib.sha256(code.encode('utf-8')).hexdigest()

    def _filter_java_stderr(self, stderr_str: str) -> str:
        return self._filter_java_output(stderr_str)

    def _filter_java_stdout(self, stdout_str: str) -> str:
        return self._filter_java_output(stdout_str)

    def _filter_java_output(self, output_str: str) -> str:
        filtered_lines = []
        info_patterns = [
            r'^Picked up JAVA_TOOL_OPTIONS:',
            r'^Picked up _JAVA_OPTIONS:',
            r'^OpenJDK 64-Bit Server VM warning:',
            r'^Java HotSpot\(TM\) 64-Bit Server VM warning:',
        ]
        
        for line in output_str.split('\n'):
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            is_info = False
            for pattern in info_patterns:
                if re.match(pattern, line_stripped):
                    is_info = True
                    break
            
            if not is_info:
                filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)

    async def _get_java_cache(self, code_hash: str) -> Optional[Tuple[str, str]]:
        async with self._java_cache_lock:
            if code_hash in self._java_compile_cache:
                file_name, class_name, timestamp = self._java_compile_cache[code_hash]
                return file_name, class_name
            return None

    async def _set_java_cache(self, code_hash: str, file_name: str, class_name: str) -> None:
        async with self._java_cache_lock:
            self._java_compile_cache[code_hash] = (file_name, class_name, datetime.now(timezone.utc))
            if len(self._java_compile_cache) > JAVA_COMPILE_CACHE_MAX_SIZE:
                sorted_cache = sorted(self._java_compile_cache.items(), key=lambda x: x[1][2])
                for key, _ in sorted_cache[:len(sorted_cache) - JAVA_COMPILE_CACHE_MAX_SIZE // 2]:
                    del self._java_compile_cache[key]

    async def _clear_java_cache(self) -> None:
        async with self._java_cache_lock:
            self._java_compile_cache.clear()

    async def create_session(self, language: str, image_tag: Optional[str] = None) -> str:
        async with self._global_lock:
            sessions = await db_manager.get_all_sessions()
            running_sessions = [s for s in sessions if s.status == "running"]
            if len(running_sessions) >= MAX_CONTAINERS:
                raise Exception(f"Maximum number of containers ({MAX_CONTAINERS}) reached. Please stop some containers first.")

        image_name = self._get_image_name(language, image_tag)
        await self._ensure_image(image_name)
        
        session_id = str(uuid.uuid4())
        container_name = f"{CONTAINER_PREFIX}{session_id[:8]}"
        
        sandbox_dir = Path(f"/tmp/sandbox-{session_id[:8]}")
        sandbox_dir.mkdir(exist_ok=True)
        
        site_packages_dir = sandbox_dir / SITE_PACKAGES_DIR
        site_packages_dir.mkdir(exist_ok=True)

        container_id = None
        try:
            docker_run_cmd = [
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
                "--tmpfs", "/var/tmp"
            ]
            
            if language == "python":
                docker_run_cmd.extend([
                    "--tmpfs", "/tmp:noexec",
                    "-v", f"{site_packages_dir}:{SITE_PACKAGES_MOUNT_PATH}:rw",
                    "-e", f"PYTHONPATH={SITE_PACKAGES_MOUNT_PATH}"
                ])
            elif language == "javascript":
                docker_run_cmd.extend([
                    "--tmpfs", "/tmp:noexec"
                ])
            elif language == "go":
                docker_run_cmd.extend([
                    "--tmpfs", "/tmp:exec,size=1g",
                    "-e", "GOPATH=/go",
                    "-e", "GOCACHE=/tmp/go-cache",
                    "-e", "GOMODCACHE=/tmp/go-modcache",
                    "--tmpfs", "/tmp/go-cache:size=512m",
                    "--tmpfs", "/tmp/go-modcache:size=512m",
                    "--ulimit", "nproc=512:512",
                    "--ulimit", "nofile=1024:1024",
                    "--pids-limit", "256"
                ])
            elif language == "c" or language == "cpp" or language == "c++":
                docker_run_cmd.extend([
                    "--tmpfs", "/tmp:exec,size=1g",
                    "--ulimit", "nproc=512:512",
                    "--ulimit", "nofile=1024:1024",
                    "--pids-limit", "256"
                ])
            elif language == "java":
                docker_run_cmd.extend([
                    "--tmpfs", "/tmp:exec,size=2g",
                    "--ulimit", "nproc=1024:1024",
                    "--ulimit", "nofile=4096:4096",
                    "--pids-limit", "512",
                    "-e", "JAVA_TOOL_OPTIONS=-Xmx512m -Xms256m",
                    "-e", "GRADLE_USER_HOME=/tmp/gradle",
                    "-e", "MAVEN_OPTS=-Xmx512m",
                    "--tmpfs", "/tmp/gradle:size=512m",
                    "--tmpfs", "/tmp/maven:size=512m"
                ])
            elif language == "lua":
                docker_run_cmd.extend([
                    "--tmpfs", "/tmp:noexec"
                ])
            
            docker_run_cmd.extend([
                image_name,
                "sleep", "infinity"
            ])
            
            result = await asyncio.create_subprocess_exec(
                *docker_run_cmd,
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
                cmd = [
                    "docker", "exec",
                    "--env", f"PYTHONPATH={SITE_PACKAGES_MOUNT_PATH}",
                    session.container_id,
                    "python3", "-u", f"/sandbox/{file_name}"
                ]
            elif session.language == "javascript":
                file_name = "exec.js"
                file_path = sandbox_dir / file_name
                file_path.write_text(code)
                cmd = ["docker", "exec", session.container_id, "node", f"/sandbox/{file_name}"]
            elif session.language == "go":
                file_name = "exec.go"
                file_path = sandbox_dir / file_name
                file_path.write_text(code)
                cmd = ["docker", "exec", session.container_id, "go", "run", f"/sandbox/{file_name}"]
            elif session.language == "c":
                file_name = "exec.c"
                file_path = sandbox_dir / file_name
                file_path.write_text(code)
                compile_and_run = f"gcc -o /sandbox/exec /sandbox/{file_name} 2>&1 && /sandbox/exec"
                cmd = ["docker", "exec", session.container_id, "sh", "-c", compile_and_run]
            elif session.language == "cpp" or session.language == "c++":
                file_name = "exec.cpp"
                file_path = sandbox_dir / file_name
                file_path.write_text(code)
                compile_and_run = f"g++ -o /sandbox/exec /sandbox/{file_name} 2>&1 && /sandbox/exec"
                cmd = ["docker", "exec", session.container_id, "sh", "-c", compile_and_run]
            elif session.language == "java":
                file_name, prepared_code = self._prepare_java_code(code)
                code_hash = self._compute_java_code_hash(prepared_code)
                class_name = file_name[:-5]
                
                jvm_opts = "-XX:+TieredCompilation -XX:TieredStopAtLevel=1"
                
                compile_and_run = f"cat > /tmp/{file_name} << 'JAVA_EOF'\n{prepared_code}\nJAVA_EOF\ncd /tmp && javac -encoding UTF-8 -O {file_name} 2>&1 && java {jvm_opts} -cp /tmp {class_name}"
                cmd = ["docker", "exec", session.container_id, "sh", "-c", compile_and_run]
            elif session.language == "lua":
                file_name = "exec.lua"
                file_path = sandbox_dir / file_name
                file_path.write_text(code)
                cmd = ["docker", "exec", session.container_id, "lua", f"/sandbox/{file_name}"]
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
                
                stdout_str = stdout.decode('utf-8', errors='replace')
                stderr_str = stderr.decode('utf-8', errors='replace')
                
                if session.language == "java":
                    filtered_stdout = self._filter_java_stdout(stdout_str)
                    filtered_stderr = self._filter_java_stderr(stderr_str)
                else:
                    filtered_stdout = stdout_str
                    filtered_stderr = stderr_str
                
                return ExecutionResult(
                    session_id=session_id,
                    output=filtered_stdout,
                    error=filtered_stderr,
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
            created_str = data.get("Created", "").replace("Z", "+00:00")
            created_str = re.sub(r'(\.\d{6})\d+([+-]\d{2}:\d{2})$', r'\1\2', created_str)
            created_at = datetime.fromisoformat(created_str)

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
            
            sandbox_dir = Path(f"/tmp/sandbox-{session_id[:8]}")
            site_packages_dir = sandbox_dir / SITE_PACKAGES_DIR
            
            if not site_packages_dir.exists():
                logger.warning(f"Site-packages directory not found, creating: {site_packages_dir}")
                site_packages_dir.mkdir(exist_ok=True)
            
            image_name = self._get_image_name("python")
            try:
                details = await self.get_container_details(session_id)
                if details.image:
                    image_name = details.image
            except Exception:
                pass
            
            logger.info(f"Installing package '{full_package}' using temp container, image={image_name}")
            
            exit_code, output, error = await self._run_temp_install_container(
                image_name=image_name,
                site_packages_dir=site_packages_dir,
                full_package=full_package,
                timeout=timeout
            )
            
            success = exit_code == 0
            
            if success:
                installed_version = await self._get_installed_version_from_site_packages(
                    site_packages_dir=site_packages_dir,
                    package_name=package_name
                )
                
                if not installed_version:
                    try:
                        installed_version = await self._get_installed_version(session.container_id, package_name)
                    except Exception:
                        pass
                
                if not installed_version:
                    installed_version = version or ""
                
                await db_manager.add_installed_package(session_id, package_name, installed_version)
                await db_manager.update_session_activity(session_id)
                
                logger.info(f"Package '{package_name}' installed successfully, version={installed_version}")
                
                return PackageInstallResult(
                    session_id=session_id,
                    package_name=package_name,
                    version=installed_version,
                    success=True,
                    output=output,
                    error=error
                )
            else:
                logger.error(f"Package installation failed for '{package_name}': {error}")
                return PackageInstallResult(
                    session_id=session_id,
                    package_name=package_name,
                    version=version or "",
                    success=False,
                    output=output,
                    error=error
                )

    async def _run_temp_install_container(
        self,
        image_name: str,
        site_packages_dir: Path,
        full_package: str,
        timeout: int
    ) -> Tuple[int, str, str]:
        install_container_name = f"sandbox-install-{uuid.uuid4().hex[:8]}"
        
        install_script = f'''
set -e
echo "Installing {full_package}..."
mkdir -p /tmp/install
pip3 install --no-cache-dir --target=/tmp/install "{full_package}"
echo "Copying installed files to {SITE_PACKAGES_MOUNT_PATH}..."
if [ -d "/tmp/install" ]; then
    cp -r /tmp/install/* "{SITE_PACKAGES_MOUNT_PATH}/" 2>/dev/null || true
fi
echo "Installation completed successfully"
'''
        
        try:
            docker_run_cmd = [
                "docker", "run",
                "--rm",
                "--name", install_container_name,
                "--memory", MEMORY_LIMIT,
                "--cpus", str(CPU_LIMIT),
                "--ulimit", "nproc=128:128",
                "--ulimit", "nofile=256:256",
                "--cap-drop", "ALL",
                "--security-opt", "no-new-privileges",
                "--pids-limit", "64",
                "-v", f"{site_packages_dir}:{SITE_PACKAGES_MOUNT_PATH}:rw",
                "-e", f"PYTHONPATH={SITE_PACKAGES_MOUNT_PATH}",
                "--tmpfs", "/tmp:size=512m",
                "--tmpfs", "/var/tmp:size=64m",
                image_name,
                "sh", "-c",
                install_script
            ]
            
            logger.info(f"Starting install container for package: {full_package}")
            
            proc = await asyncio.create_subprocess_exec(
                *docker_run_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout
                )
                exit_code = proc.returncode
                
                logger.info(f"Install container completed with exit code {exit_code}")
                return (
                    exit_code,
                    stdout.decode('utf-8', errors='replace'),
                    stderr.decode('utf-8', errors='replace')
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                logger.warning(f"Install container timed out for package: {full_package}")
                return (-1, "", f"Package installation timed out after {timeout} seconds")
                
        except Exception as e:
            logger.error(f"Error in install container: {e}")
            return (-1, "", str(e))
        finally:
            try:
                result = await asyncio.create_subprocess_exec(
                    "docker", "rm", "-f", install_container_name,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await result.communicate()
            except Exception:
                pass

    async def _get_installed_version(self, container_id: str, package_name: str) -> str:
        try:
            result = await asyncio.create_subprocess_exec(
                "docker", "exec",
                "--env", f"PYTHONPATH={SITE_PACKAGES_MOUNT_PATH}",
                container_id,
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
    
    async def _get_installed_version_from_site_packages(
        self,
        site_packages_dir: Path,
        package_name: str
    ) -> str:
        try:
            import importlib.metadata
            import sys
            
            original_path = sys.path.copy()
            try:
                sys.path.insert(0, str(site_packages_dir))
                version = importlib.metadata.version(package_name)
                return version
            except importlib.metadata.PackageNotFoundError:
                dir_contents = list(site_packages_dir.glob(f"{package_name.replace('-', '_')}*"))
                dir_contents += list(site_packages_dir.glob(f"{package_name}*"))
                
                for item in dir_contents:
                    if item.is_dir() and item.name.endswith('.dist-info'):
                        metadata_file = item / "METADATA"
                        if metadata_file.exists():
                            content = metadata_file.read_text()
                            for line in content.split('\n'):
                                if line.startswith('Version:'):
                                    return line.split(':', 1)[1].strip()
                return ""
            finally:
                sys.path = original_path
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

        packages_dict = {}
        
        sandbox_dir = Path(f"/tmp/sandbox-{session_id[:8]}")
        site_packages_dir = sandbox_dir / SITE_PACKAGES_DIR
        
        if site_packages_dir.exists():
            try:
                for item in site_packages_dir.iterdir():
                    if item.is_dir() and item.name.endswith('.dist-info'):
                        try:
                            metadata_file = item / "METADATA"
                            if metadata_file.exists():
                                content = metadata_file.read_text()
                                name = None
                                version = None
                                for line in content.split('\n'):
                                    if line.startswith('Name:'):
                                        name = line.split(':', 1)[1].strip()
                                    elif line.startswith('Version:'):
                                        version = line.split(':', 1)[1].strip()
                                    if name and version:
                                        break
                                if name and version:
                                    packages_dict[name] = version
                        except Exception as e:
                            logger.warning(f"Failed to read metadata from {item}: {e}")
            except Exception as e:
                logger.error(f"Failed to scan site-packages directory: {e}")

        try:
            result = await asyncio.create_subprocess_exec(
                "docker", "exec",
                "--env", f"PYTHONPATH={SITE_PACKAGES_MOUNT_PATH}",
                session.container_id,
                "pip3", "list", "--format=freeze",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()

            if result.returncode == 0:
                output = stdout.decode('utf-8', errors='replace')
                for line in output.strip().split('\n'):
                    if line and '==' in line:
                        name, version = line.split('==', 1)
                        if name not in packages_dict:
                            packages_dict[name] = version

            packages = []
            for name, version in packages_dict.items():
                packages.append({"name": name, "version": version})
                await db_manager.add_installed_package(session_id, name, version)

            await db_manager.update_session_activity(session_id)

            packages.sort(key=lambda x: x["name"].lower())
            return PackageListResult(session_id=session_id, packages=packages)

        except Exception as e:
            logger.error(f"Failed to list packages for session {session_id}: {e}")
            
            packages = []
            for name, version in packages_dict.items():
                packages.append({"name": name, "version": version})
            
            if packages:
                packages.sort(key=lambda x: x["name"].lower())
                return PackageListResult(session_id=session_id, packages=packages)
            
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
            sandbox_dir = Path(f"/tmp/sandbox-{session_id[:8]}")
            site_packages_dir = sandbox_dir / SITE_PACKAGES_DIR
            
            if not site_packages_dir.exists():
                return PackageInstallResult(
                    session_id=session_id,
                    package_name=package_name,
                    version="",
                    success=False,
                    output="",
                    error=f"Site-packages directory not found: {site_packages_dir}"
                )
            
            import shutil
            
            package_name_lower = package_name.lower().replace('-', '_')
            package_name_original = package_name
            
            removed_count = 0
            errors = []
            
            try:
                for item in site_packages_dir.iterdir():
                    if not item.is_dir():
                        continue
                    
                    item_name_lower = item.name.lower().replace('-', '_')
                    
                    if item_name_lower == package_name_lower or \
                       item_name_lower.startswith(package_name_lower + '-') or \
                       item_name_lower.startswith(package_name_lower + '.') or \
                       item_name_lower.endswith('.dist-info') and item_name_lower.startswith(package_name_lower + '-') or \
                       item_name_lower.endswith('.egg-info') and item_name_lower.startswith(package_name_lower + '-'):
                        
                        base_name = item_name_lower
                        for suffix in ['.dist-info', '.egg-info']:
                            if base_name.endswith(suffix):
                                base_name = base_name[:-len(suffix)]
                                break
                        
                        if base_name == package_name_lower or base_name.startswith(package_name_lower + '-'):
                            try:
                                if item.is_dir():
                                    shutil.rmtree(item)
                                else:
                                    item.unlink()
                                removed_count += 1
                                logger.info(f"Removed package directory: {item}")
                            except Exception as e:
                                errors.append(f"Failed to remove {item}: {e}")
                                logger.error(f"Failed to remove {item}: {e}")
                
                try:
                    for pycache_dir in site_packages_dir.rglob('__pycache__'):
                        if package_name_lower in str(pycache_dir).lower():
                            try:
                                shutil.rmtree(pycache_dir)
                                removed_count += 1
                            except Exception:
                                pass
                except Exception:
                    pass
                
                if removed_count > 0:
                    await db_manager.remove_installed_package(session_id, package_name)
                    await db_manager.update_session_activity(session_id)
                    
                    logger.info(f"Uninstalled package '{package_name}', removed {removed_count} items")
                    
                    return PackageInstallResult(
                        session_id=session_id,
                        package_name=package_name,
                        version="",
                        success=True,
                        output=f"Removed {removed_count} items",
                        error="; ".join(errors) if errors else ""
                    )
                else:
                    return PackageInstallResult(
                        session_id=session_id,
                        package_name=package_name,
                        version="",
                        success=False,
                        output="",
                        error=f"Package '{package_name}' not found in site-packages"
                    )
                    
            except Exception as e:
                logger.error(f"Error during package uninstallation: {e}")
                return PackageInstallResult(
                    session_id=session_id,
                    package_name=package_name,
                    version="",
                    success=False,
                    output="",
                    error=str(e)
                )


container_manager = ContainerManager()
