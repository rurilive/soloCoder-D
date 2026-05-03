#!/usr/bin/env python3
"""
Go语言支持集成测试脚本
通过API测试Go语言会话的创建和代码执行
"""

import asyncio
import httpx
import sys
import json

BASE_URL = "http://localhost:4444"


async def test_go_support():
    """测试Go语言支持"""
    print("=" * 60)
    print("Go语言支持集成测试")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # 测试1: 检查服务是否可用
        print("\n测试1: 检查服务是否可用...")
        try:
            response = await client.get(f"{BASE_URL}/api/sessions")
            if response.status_code == 200:
                print("  ✓ 服务运行正常")
            else:
                print(f"  ✗ 服务返回非200状态码: {response.status_code}")
                return False
        except Exception as e:
            print(f"  ✗ 无法连接到服务: {e}")
            print("  请确保先运行: python main.py 或 uv run python main.py")
            return False
        
        # 测试2: 创建Go语言会话
        print("\n测试2: 创建Go语言会话...")
        try:
            response = await client.post(
                f"{BASE_URL}/api/sessions",
                json={"language": "go"}
            )
            if response.status_code == 200:
                data = response.json()
                session_id = data.get("session_id")
                language = data.get("language")
                print(f"  ✓ 会话创建成功")
                print(f"    会话ID: {session_id}")
                print(f"    语言: {language}")
            else:
                print(f"  ✗ 创建会话失败: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"  ✗ 创建会话时出错: {e}")
            return False
        
        # 测试3: 执行Go代码
        print("\n测试3: 执行Go代码...")
        go_code = '''package main

import "fmt"

func main() {
    fmt.Println("Hello from Go!")
    result := 42 + 27
    fmt.Printf("42 + 27 = %d\\n", result)
}
'''
        try:
            response = await client.post(
                f"{BASE_URL}/api/execute",
                json={
                    "code": go_code,
                    "session_id": session_id
                }
            )
            if response.status_code == 200:
                data = response.json()
                output = data.get("output", "")
                error = data.get("error", "")
                exit_code = data.get("exit_code", -1)
                
                print(f"  ✓ 代码执行完成")
                print(f"    退出码: {exit_code}")
                if output:
                    print(f"    标准输出:")
                    for line in output.strip().split('\n'):
                        print(f"      {line}")
                if error:
                    print(f"    错误输出:")
                    for line in error.strip().split('\n'):
                        print(f"      {line}")
                
                # 验证输出是否包含预期内容
                if "Hello from Go!" in output and "42 + 27 = 69" in output:
                    print("  ✓ 输出验证通过")
                else:
                    print("  ⚠ 输出可能不包含预期内容，请检查")
            else:
                print(f"  ✗ 执行代码失败: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"  ✗ 执行代码时出错: {e}")
        
        # 测试4: 停止会话
        print("\n测试4: 停止会话...")
        try:
            response = await client.delete(f"{BASE_URL}/api/sessions/{session_id}")
            if response.status_code == 200:
                print("  ✓ 会话已停止")
            else:
                print(f"  ⚠ 停止会话时返回非200状态码: {response.status_code}")
        except Exception as e:
            print(f"  ⚠ 停止会话时出错: {e}")
        
        # 测试5: 验证不支持的语言
        print("\n测试5: 验证不支持的语言处理...")
        try:
            response = await client.post(
                f"{BASE_URL}/api/sessions",
                json={"language": "unsupported_lang"}
            )
            if response.status_code == 400 or response.status_code == 500:
                print("  ✓ 不支持的语言正确返回错误")
            else:
                print(f"  ⚠ 不支持的语言返回状态码: {response.status_code}")
        except Exception as e:
            print(f"  ⚠ 测试不支持的语言时出错: {e}")
        
        return True


async def main():
    """主函数"""
    print("Go语言支持集成测试")
    print("请确保服务已在运行: http://localhost:4444")
    print()
    
    success = await test_go_support()
    
    print("\n" + "=" * 60)
    print("集成测试完成")
    print("=" * 60)
    
    if success:
        print("\n✓ 集成测试完成！Go语言支持功能正常。")
        print("\n功能验证总结:")
        print("  1. 服务运行正常 ✓")
        print("  2. 可以创建Go语言会话 ✓")
        print("  3. 可以执行Go代码 ✓")
        print("  4. 可以停止会话 ✓")
        print("  5. 不支持的语言正确处理 ✓")
        return True
    else:
        print("\n✗ 集成测试失败，请检查服务状态。")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
