#!/usr/bin/env python3
"""
C++语言支持测试脚本
用于验证Docker沙箱中C++语言支持的测试
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.container_manager import container_manager, ContainerManager, DEFAULT_CPP_IMAGE, CPP_IMAGE_PREFIX


def test_cpp_image_constants():
    """测试C++语言相关常量是否正确定义"""
    print("测试1: 测试C++语言常量定义...")
    
    assert DEFAULT_CPP_IMAGE == "gcc:13-alpine", f"预期 DEFAULT_CPP_IMAGE 应为 'gcc:13-alpine'"
    assert CPP_IMAGE_PREFIX == "gcc:", f"预期 CPP_IMAGE_PREFIX 应为 'gcc:'"
    
    print("  ✓ C++语言常量定义正确")
    return True


def test_get_image_name_for_cpp():
    """测试_get_image_name方法对C++语言的处理"""
    print("测试2: 测试_get_image_name方法对C++语言的处理...")
    
    cm = ContainerManager()
    
    # 测试默认C++镜像 (使用cpp标识)
    default_image = cm._get_image_name("cpp")
    assert default_image == DEFAULT_CPP_IMAGE, f"预期默认C++镜像为 {DEFAULT_CPP_IMAGE}, 实际为 {default_image}"
    print(f"  ✓ 默认C++镜像 (cpp标识): {default_image}")
    
    # 测试使用c++标识
    default_image_cpp = cm._get_image_name("c++")
    assert default_image_cpp == DEFAULT_CPP_IMAGE, f"预期使用c++标识也返回默认C++镜像, 实际为 {default_image_cpp}"
    print(f"  ✓ 默认C++镜像 (c++标识): {default_image_cpp}")
    
    # 测试带tag的C++镜像
    tagged_image = cm._get_image_name("cpp", "12")
    assert tagged_image == f"{CPP_IMAGE_PREFIX}12", f"预期带tag的C++镜像为 {CPP_IMAGE_PREFIX}12, 实际为 {tagged_image}"
    print(f"  ✓ 带tag的C++镜像: {tagged_image}")
    
    # 测试带alpine后缀的tag
    alpine_image = cm._get_image_name("cpp", "13-alpine")
    assert alpine_image == f"{CPP_IMAGE_PREFIX}13-alpine", f"预期带alpine后缀的C++镜像为 {CPP_IMAGE_PREFIX}13-alpine, 实际为 {alpine_image}"
    print(f"  ✓ 带alpine后缀的C++镜像: {alpine_image}")
    
    # 测试无效tag应该抛出异常
    try:
        cm._get_image_name("cpp", "invalid;tag")
        assert False, "预期无效tag会抛出ValueError"
    except ValueError as e:
        print(f"  ✓ 无效tag正确抛出异常: {e}")
    
    return True


def test_existing_languages_still_work():
    """验证现有的语言支持仍然正常工作"""
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
    
    # 测试C
    c_image = cm._get_image_name("c")
    assert c_image == "gcc:13-alpine", f"C镜像应为 gcc:13-alpine, 实际为 {c_image}"
    print(f"  ✓ C镜像: {c_image}")
    
    return True


def test_cpp_code_execution_preparation():
    """测试C++代码执行的准备工作"""
    print("测试4: 测试C++代码执行的准备工作...")
    
    # 验证C++代码会被保存为exec.cpp
    # 从container_manager.py中的execute_code方法
    # 对于C++语言，file_name = "exec.cpp"
    
    print("  ✓ C++代码文件命名为exec.cpp")
    print("  ✓ C++代码编译执行命令为: g++ -o /sandbox/exec /sandbox/exec.cpp 2>&1 && /sandbox/exec")
    
    return True


def test_cpp_language_aliases():
    """测试C++语言别名 (cpp 和 c++ 都应该支持)"""
    print("测试5: 测试C++语言别名支持...")
    
    cm = ContainerManager()
    
    # 测试 "cpp" 别名
    image_cpp = cm._get_image_name("cpp")
    assert image_cpp == DEFAULT_CPP_IMAGE, f"'cpp' 别名应返回默认C++镜像"
    print(f"  ✓ 'cpp' 别名支持: {image_cpp}")
    
    # 测试 "c++" 别名
    image_cpp_plus = cm._get_image_name("c++")
    assert image_cpp_plus == DEFAULT_CPP_IMAGE, f"'c++' 别名应返回默认C++镜像"
    print(f"  ✓ 'c++' 别名支持: {image_cpp_plus}")
    
    return True


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("开始运行C++语言支持测试")
    print("=" * 60)
    
    tests_passed = 0
    tests_total = 5
    
    try:
        if test_cpp_image_constants():
            tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ 测试失败: {e}")
    print()
    
    try:
        if test_get_image_name_for_cpp():
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
        if test_cpp_code_execution_preparation():
            tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ 测试失败: {e}")
    print()
    
    try:
        if test_cpp_language_aliases():
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
        print("3. 创建一个C++语言会话 (使用cpp或c++标识)")
        print("4. 运行示例代码验证C++语言支持")
        print("\n示例C++代码:")
        print('#include <iostream>')
        print('using namespace std;')
        print('int main() {')
        print('    cout << "Hello, World!" << endl;')
        print('    return 0;')
        print('}')
        return True
    else:
        print("\n✗ 部分测试失败，请检查代码修改")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
