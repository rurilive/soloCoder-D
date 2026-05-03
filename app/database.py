import asyncio
import aiosqlite
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass, field

DB_PATH = Path(__file__).parent.parent / "sandbox.db"


@dataclass
class ContainerSession:
    id: str
    language: str
    container_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "running"
    last_active_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class InstalledPackage:
    id: int
    session_id: str
    name: str
    version: str
    installed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AuditLog:
    id: int
    session_id: str
    language: str
    action: str
    code_hash: str
    code_preview: str
    output: str
    error: str
    exit_code: int
    execution_time_ms: int
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class DatabaseManager:
    def __init__(self):
        self._lock = asyncio.Lock()

    async def init_db(self):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    language TEXT NOT NULL,
                    container_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    last_active_at TEXT NOT NULL
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS installed_packages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    installed_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
                    UNIQUE(session_id, name)
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    language TEXT NOT NULL,
                    action TEXT NOT NULL,
                    code_hash TEXT NOT NULL,
                    code_preview TEXT NOT NULL,
                    output TEXT NOT NULL,
                    error TEXT NOT NULL,
                    exit_code INTEGER NOT NULL,
                    execution_time_ms INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_logs_session_id ON audit_logs(session_id)
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at)
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_logs_language ON audit_logs(language)
            """)

            await db.commit()

    async def create_session(self, session: ContainerSession) -> None:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO sessions (id, language, container_id, created_at, status, last_active_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session.id,
                session.language,
                session.container_id,
                session.created_at.isoformat(),
                session.status,
                session.last_active_at.isoformat()
            ))
            await db.commit()

    async def get_session(self, session_id: str) -> Optional[ContainerSession]:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return ContainerSession(
                        id=row["id"],
                        language=row["language"],
                        container_id=row["container_id"],
                        created_at=datetime.fromisoformat(row["created_at"]),
                        status=row["status"],
                        last_active_at=datetime.fromisoformat(row["last_active_at"])
                    )
        return None

    async def get_all_sessions(self) -> List[ContainerSession]:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM sessions") as cursor:
                rows = await cursor.fetchall()
                return [
                    ContainerSession(
                        id=row["id"],
                        language=row["language"],
                        container_id=row["container_id"],
                        created_at=datetime.fromisoformat(row["created_at"]),
                        status=row["status"],
                        last_active_at=datetime.fromisoformat(row["last_active_at"])
                    )
                    for row in rows
                ]

    async def update_session_status(self, session_id: str, status: str) -> None:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                UPDATE sessions 
                SET status = ?, last_active_at = ?
                WHERE id = ?
            """, (
                status,
                datetime.now(timezone.utc).isoformat(),
                session_id
            ))
            await db.commit()

    async def update_session_activity(self, session_id: str) -> None:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                UPDATE sessions 
                SET last_active_at = ?
                WHERE id = ?
            """, (
                datetime.now(timezone.utc).isoformat(),
                session_id
            ))
            await db.commit()

    async def delete_session(self, session_id: str) -> None:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            await db.commit()

    async def clear_all_sessions(self) -> None:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM sessions")
            await db.commit()

    async def add_installed_package(self, session_id: str, name: str, version: str) -> None:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT OR REPLACE INTO installed_packages (session_id, name, version, installed_at)
                VALUES (?, ?, ?, ?)
            """, (
                session_id,
                name,
                version,
                datetime.now(timezone.utc).isoformat()
            ))
            await db.commit()

    async def get_installed_packages(self, session_id: str) -> List[InstalledPackage]:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM installed_packages WHERE session_id = ? ORDER BY name",
                (session_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [
                    InstalledPackage(
                        id=row["id"],
                        session_id=row["session_id"],
                        name=row["name"],
                        version=row["version"],
                        installed_at=datetime.fromisoformat(row["installed_at"])
                    )
                    for row in rows
                ]

    async def remove_installed_package(self, session_id: str, name: str) -> None:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "DELETE FROM installed_packages WHERE session_id = ? AND name = ?",
                (session_id, name)
            )
            await db.commit()

    async def clear_session_packages(self, session_id: str) -> None:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "DELETE FROM installed_packages WHERE session_id = ?",
                (session_id,)
            )
            await db.commit()

    async def create_audit_log(
        self,
        session_id: str,
        language: str,
        action: str,
        code_hash: str,
        code_preview: str,
        output: str,
        error: str,
        exit_code: int,
        execution_time_ms: int
    ) -> None:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO audit_logs (
                    session_id, language, action, code_hash, code_preview,
                    output, error, exit_code, execution_time_ms, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                language,
                action,
                code_hash,
                code_preview,
                output,
                error,
                exit_code,
                execution_time_ms,
                datetime.now(timezone.utc).isoformat()
            ))
            await db.commit()

    async def get_audit_logs_by_session(self, session_id: str, limit: int = 100) -> List[AuditLog]:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM audit_logs WHERE session_id = ? ORDER BY created_at DESC LIMIT ?",
                (session_id, limit)
            ) as cursor:
                rows = await cursor.fetchall()
                return [
                    AuditLog(
                        id=row["id"],
                        session_id=row["session_id"],
                        language=row["language"],
                        action=row["action"],
                        code_hash=row["code_hash"],
                        code_preview=row["code_preview"],
                        output=row["output"],
                        error=row["error"],
                        exit_code=row["exit_code"],
                        execution_time_ms=row["execution_time_ms"],
                        created_at=datetime.fromisoformat(row["created_at"])
                    )
                    for row in rows
                ]

    async def get_audit_logs_by_language(self, language: str, limit: int = 100) -> List[AuditLog]:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM audit_logs WHERE language = ? ORDER BY created_at DESC LIMIT ?",
                (language, limit)
            ) as cursor:
                rows = await cursor.fetchall()
                return [
                    AuditLog(
                        id=row["id"],
                        session_id=row["session_id"],
                        language=row["language"],
                        action=row["action"],
                        code_hash=row["code_hash"],
                        code_preview=row["code_preview"],
                        output=row["output"],
                        error=row["error"],
                        exit_code=row["exit_code"],
                        execution_time_ms=row["execution_time_ms"],
                        created_at=datetime.fromisoformat(row["created_at"])
                    )
                    for row in rows
                ]

    async def get_all_audit_logs(self, limit: int = 100) -> List[AuditLog]:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [
                    AuditLog(
                        id=row["id"],
                        session_id=row["session_id"],
                        language=row["language"],
                        action=row["action"],
                        code_hash=row["code_hash"],
                        code_preview=row["code_preview"],
                        output=row["output"],
                        error=row["error"],
                        exit_code=row["exit_code"],
                        execution_time_ms=row["execution_time_ms"],
                        created_at=datetime.fromisoformat(row["created_at"])
                    )
                    for row in rows
                ]

    async def clear_audit_logs(self) -> None:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM audit_logs")
            await db.commit()


db_manager = DatabaseManager()
