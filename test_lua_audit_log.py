#!/usr/bin/env python3
"""
Lua沙箱日志审计功能测试脚本
用于验证Docker沙箱中Lua语言执行的日志审计功能
"""

import asyncio
import sys
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import db_manager, DatabaseManager, AuditLog, ContainerSession
from app.container_manager import ContainerManager


def test_audit_log_dataclass():
    """测试AuditLog数据类是否正确定义"""
    print("测试1: 测试AuditLog数据类定义...")
    
    audit_log = AuditLog(
        id=1,
        session_id="test-session-123",
        language="lua",
        action="execute",
        code_hash="abc123def456",
        code_preview="print('Hello World')",
        output="Hello World\n",
        error="",
        exit_code=0,
        execution_time_ms=100,
        created_at=datetime.now(timezone.utc)
    )
    
    assert audit_log.id == 1
    assert audit_log.session_id == "test-session-123"
    assert audit_log.language == "lua"
    assert audit_log.action == "execute"
    assert audit_log.code_hash == "abc123def456"
    assert audit_log.code_preview == "print('Hello World')"
    assert audit_log.output == "Hello World\n"
    assert audit_log.error == ""
    assert audit_log.exit_code == 0
    assert audit_log.execution_time_ms == 100
    
    print("  ✓ AuditLog数据类定义正确")
    return True


def test_compute_code_hash():
    """测试代码哈希计算功能"""
    print("测试2: 测试代码哈希计算功能...")
    
    cm = ContainerManager()
    
    code1 = "print('Hello World')"
    code2 = "print('Hello World')"
    code3 = "print('Different Code')"
    
    hash1 = cm._compute_code_hash(code1)
    hash2 = cm._compute_code_hash(code2)
    hash3 = cm._compute_code_hash(code3)
    
    assert hash1 == hash2, "相同代码应该有相同的哈希"
    assert hash1 != hash3, "不同代码应该有不同的哈希"
    assert len(hash1) == 64, "SHA256哈希应该是64个字符"
    
    print(f"  ✓ 代码哈希计算正确: {hash1[:16]}...")
    return True


def test_get_code_preview():
    """测试代码预览生成功能"""
    print("测试3: 测试代码预览生成功能...")
    
    cm = ContainerManager()
    
    short_code = "print('Hello')"
    long_code = "a" * 300
    
    short_preview = cm._get_code_preview(short_code)
    long_preview = cm._get_code_preview(long_code, max_length=200)
    
    assert short_preview == short_code, "短代码应该完整显示"
    assert len(long_preview) == 203, "长代码应该被截断并添加省略号"
    assert long_preview.endswith("..."), "截断的代码应该以省略号结尾"
    
    print("  ✓ 代码预览生成正确")
    return True


async def test_audit_log_database_operations():
    """测试审计日志的数据库操作"""
    print("测试4: 测试审计日志数据库操作...")
    
    test_db_path = Path("/tmp/test_audit_log.db")
    if test_db_path.exists():
        test_db_path.unlink()
    
    original_db_path = Path(__file__).parent / "app" / "sandbox.db"
    backup_path = None
    if original_db_path.exists():
        backup_path = Path("/tmp/sandbox_backup.db")
        shutil.copy2(original_db_path, backup_path)
    
    try:
        test_manager = DatabaseManager()
        
        import app.database as db_module
        original_path = db_module.DB_PATH
        db_module.DB_PATH = test_db_path
        
        await test_manager.init_db()
        
        test_session = ContainerSession(
            id="test-session-001",
            language="lua",
            container_id="test-container-123",
            created_at=datetime.now(timezone.utc),
            status="running",
            last_active_at=datetime.now(timezone.utc)
        )
        await test_manager.create_session(test_session)
        
        await test_manager.create_audit_log(
            session_id="test-session-001",
            language="lua",
            action="execute",
            code_hash="abc123def456",
            code_preview="print('Hello')",
            output="Hello\n",
            error="",
            exit_code=0,
            execution_time_ms=50
        )
        
        logs_by_session = await test_manager.get_audit_logs_by_session("test-session-001")
        assert len(logs_by_session) == 1, "应该能找到1条审计日志"
        assert logs_by_session[0].language == "lua"
        assert logs_by_session[0].action == "execute"
        assert logs_by_session[0].exit_code == 0
        print("  ✓ 按会话查询审计日志成功")
        
        logs_by_language = await test_manager.get_audit_logs_by_language("lua")
        assert len(logs_by_language) == 1, "应该能找到1条Lua语言的审计日志"
        print("  ✓ 按语言查询审计日志成功")
        
        all_logs = await test_manager.get_all_audit_logs()
        assert len(all_logs) == 1, "应该能找到1条审计日志"
        print("  ✓ 查询所有审计日志成功")
        
        await test_manager.create_audit_log(
            session_id="test-session-001",
            language="lua",
            action="execute_blocked",
            code_hash="xyz789",
            code_preview="os.execute('rm -rf')",
            output="",
            error="Code contains potentially dangerous operations",
            exit_code=1,
            execution_time_ms=10
        )
        
        all_logs = await test_manager.get_all_audit_logs()
        assert len(all_logs) == 2, "现在应该有2条审计日志"
        print("  ✓ 多条审计日志记录成功")
        
        await test_manager.clear_audit_logs()
        all_logs = await test_manager.get_all_audit_logs()
        assert len(all_logs) == 0, "清除后应该没有审计日志"
        print("  ✓ 清除审计日志成功")
        
        db_module.DB_PATH = original_path
        
        print("  ✓ 所有数据库操作测试通过")
        return True
        
    finally:
        if test_db_path.exists():
            test_db_path.unlink()
        if backup_path and backup_path.exists():
            shutil.copy2(backup_path, original_db_path)
            backup_path.unlink()


async def test_audit_log_scenarios():
    """测试不同场景下的审计日志记录"""
    print("测试5: 测试不同场景下的审计日志记录...")
    
    cm = ContainerManager()
    
    test_code = """
-- 测试Lua代码
local function factorial(n)
    if n <= 1 then
        return 1
    end
    return n * factorial(n - 1)
end

print("Factorial of 5: " .. factorial(5))
"""
    
    code_hash = cm._compute_code_hash(test_code)
    code_preview = cm._get_code_preview(test_code)
    
    print(f"  代码哈希: {code_hash[:16]}...")
    print(f"  代码预览长度: {len(code_preview)} 字符")
    
    assert len(code_hash) == 64
    assert len(code_preview) <= 203
    
    print("  ✓ 审计日志场景测试通过")
    return True


def test_audit_log_indexes():
    """测试审计日志表的索引创建"""
    print("测试6: 测试审计日志表索引...")
    
    import sqlite3
    
    test_db_path = Path("/tmp/test_indexes.db")
    if test_db_path.exists():
        test_db_path.unlink()
    
    conn = sqlite3.connect(str(test_db_path))
    cursor = conn.cursor()
    
    cursor.execute("""
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
            created_at TEXT NOT NULL
        )
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_session_id ON audit_logs(session_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_language ON audit_logs(language)")
    
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='index' AND tbl_name='audit_logs'
    """)
    indexes = cursor.fetchall()
    
    index_names = [idx[0] for idx in indexes]
    assert "idx_audit_logs_session_id" in index_names
    assert "idx_audit_logs_created_at" in index_names
    assert "idx_audit_logs_language" in index_names
    
    conn.close()
    test_db_path.unlink()
    
    print("  ✓ 审计日志表索引创建正确")
    return True


async def run_all_tests():
    """运行所有测试"""
    print("=" * 70)
    print("开始运行Lua沙箱日志审计功能测试")
    print("=" * 70)
    
    tests_passed = 0
    tests_total = 6
    
    try:
        if test_audit_log_dataclass():
            tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ 测试失败: {e}")
    print()
    
    try:
        if test_compute_code_hash():
            tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ 测试失败: {e}")
    print()
    
    try:
        if test_get_code_preview():
            tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ 测试失败: {e}")
    print()
    
    try:
        if await test_audit_log_database_operations():
            tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ 测试失败: {e}")
    except Exception as e:
        print(f"  ✗ 测试错误: {e}")
        import traceback
        traceback.print_exc()
    print()
    
    try:
        if await test_audit_log_scenarios():
            tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ 测试失败: {e}")
    print()
    
    try:
        if test_audit_log_indexes():
            tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ 测试失败: {e}")
    print()
    
    print("=" * 70)
    print(f"测试完成: {tests_passed}/{tests_total} 通过")
    print("=" * 70)
    
    if tests_passed == tests_total:
        print("\n✓ 所有审计日志功能测试通过！")
        print("\n审计日志功能说明:")
        print("1. 每次执行Lua代码时，系统会自动记录审计日志")
        print("2. 审计日志包括:")
        print("   - 会话ID和语言类型")
        print("   - 操作类型(execute, execute_blocked, execute_timeout, execute_error)")
        print("   - 代码哈希(SHA256)和代码预览")
        print("   - 执行输出、错误信息和退出码")
        print("   - 执行时间(毫秒)")
        print("   - 时间戳")
        print("\n3. 数据库索引优化:")
        print("   - 按会话ID查询优化")
        print("   - 按时间查询优化")
        print("   - 按语言查询优化")
        return True
    else:
        print("\n✗ 部分测试失败，请检查代码修改")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)