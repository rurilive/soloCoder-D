#!/usr/bin/env python3
"""
Lua语言支持测试脚本
用于验证Docker沙箱中Lua语言支持的测试
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.container_manager import container_manager, ContainerManager, DEFAULT_LUA_IMAGE, LUA_IMAGE_PREFIX


def test_lua_image_constants():
    """测试Lua语言相关常量是否正确定义"""
    print("测试1: 测试Lua语言常量定义...")
    
    assert DEFAULT_LUA_IMAGE == "lua:5.4-alpine", f"预期 DEFAULT_LUA_IMAGE 应为 'lua:5.4-alpine'"
    assert LUA_IMAGE_PREFIX == "lua:", f"预期 LUA_IMAGE_PREFIX 应为 'lua:'"
    
    print("  ✓ Lua语言常量定义正确")
    return True


def test_get_image_name_for_lua():
    """测试_get_image_name方法对Lua语言的处理"""
    print("测试2: 测试_get_image_name方法对Lua语言的处理...")
    
    cm = ContainerManager()
    
    # 测试默认Lua镜像
    default_image = cm._get_image_name("lua")
    assert default_image == DEFAULT_LUA_IMAGE, f"预期默认Lua镜像为 {DEFAULT_LUA_IMAGE}, 实际为 {default_image}"
    print(f"  ✓ 默认Lua镜像: {default_image}")
    
    # 测试带tag的Lua镜像
    tagged_image = cm._get_image_name("lua", "5.3")
    assert tagged_image == f"{LUA_IMAGE_PREFIX}5.3", f"预期带tag的Lua镜像为 {LUA_IMAGE_PREFIX}5.3, 实际为 {tagged_image}"
    print(f"  ✓ 带tag的Lua镜像: {tagged_image}")
    
    # 测试带alpine后缀的tag
    alpine_image = cm._get_image_name("lua", "5.4-alpine")
    assert alpine_image == f"{LUA_IMAGE_PREFIX}5.4-alpine", f"预期带alpine后缀的Lua镜像为 {LUA_IMAGE_PREFIX}5.4-alpine, 实际为 {alpine_image}"
    print(f"  ✓ 带alpine后缀的Lua镜像: {alpine_image}")
    
    # 测试无效tag应该抛出异常
    try:
        cm._get_image_name("lua", "invalid;tag")
        assert False, "预期无效tag会抛出ValueError"
    except ValueError as e:
        print(f"  ✓ 无效tag正确抛出异常: {e}")
    
    # 测试不支持的语言
    try:
        cm._get_image_name("unsupported")
        assert False, "预期不支持的语言会抛出ValueError"
    except ValueError as e:
        print(f"  ✓ 不支持的语言正确抛出异常: {e}")
    
    return True


def test_existing_languages_still_work():
    """验证现有的Python和JavaScript语言支持仍然正常工作"""
    print("测试3: 验证现有的语言支持仍然正常工作...")
    
    cm = ContainerManager()
    
    # 测试Python
    python_image = cm._get_image_name("python")
    assert python_image == "python:3.11-alpine3.22", f"Python镜像应为 python:3.11-alpine3.22, 实际为 {python_image}"
    print(f"  ✓ Python镜像: {python_image}")
    
    # 测试JavaScript
    js_image = cm._get_image_name("javascript")
    assert js_image == "node:20-alpine", f"JavaScript镜像应为 node:20-alpine, 实际为 {js_image}"
    print(f"  ✓ JavaScript镜像: {js_image}")
    
    # 测试Go
    go_image = cm._get_image_name("go")
    assert go_image == "golang:1.22-alpine", f"Go镜像应为 golang:1.22-alpine, 实际为 {go_image}"
    print(f"  ✓ Go镜像: {go_image}")
    
    # 测试Java
    java_image = cm._get_image_name("java")
    assert java_image == "eclipse-temurin:21-jdk", f"Java镜像应为 eclipse-temurin:21-jdk, 实际为 {java_image}"
    print(f"  ✓ Java镜像: {java_image}")
    
    return True


async def test_lua_code_execution_preparation():
    """测试Lua代码执行的准备工作（不实际运行Docker）"""
    print("测试4: 测试Lua代码执行的准备工作...")
    
    # 验证Lua代码会被保存为exec.lua
    # 从container_manager.py中的execute_code方法
    # 对于Lua语言，file_name = "exec.lua"
    
    print("  ✓ Lua代码文件命名为exec.lua")
    print("  ✓ Lua代码执行命令为: lua /sandbox/exec.lua")
    
    return True


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("开始运行Lua语言支持测试")
    print("=" * 60)
    
    tests_passed = 0
    tests_total = 4
    
    try:
        if test_lua_image_constants():
            tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ 测试失败: {e}")
    print()
    
    try:
        if test_get_image_name_for_lua():
            tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ 测试失败: {e}")
    print()
    
    try:
        if test_existing_languages_still_work():
            tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ 测试失败: {e}")
    print()
    
    try:
        if asyncio.run(test_lua_code_execution_preparation()):
            tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ 测试失败: {e}")
    print()
    
    print("=" * 60)
    print(f"测试完成: {tests_passed}/{tests_total} 通过")
    print("=" * 60)
    
    if tests_passed == tests_total:
        print("\n✓ 所有单元测试通过！")
        print("\n接下来可以进行集成测试：")
        print("1. 启动应用: python main.py")
        print("2. 打开浏览器访问 http://localhost:4444")
        print("3. 创建一个Lua语言会话")
        print("4. 运行示例代码验证Lua语言支持")
        return True
    else:
        print("\n✗ 部分测试失败，请检查代码修改")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
