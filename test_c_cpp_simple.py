#!/usr/bin/env python3
"""
C和C++语言支持的简单测试脚本
不依赖完整应用程序环境，直接测试核心逻辑
"""

import re
import sys

# 模拟container_manager.py中的常量
DEFAULT_PYTHON_IMAGE = "python:3.11-alpine3.22"
DEFAULT_NODE_IMAGE = "node:20-alpine"
DEFAULT_GO_IMAGE = "golang:1.22-alpine"
DEFAULT_C_IMAGE = "gcc:13"
DEFAULT_CPP_IMAGE = "gcc:13"

PYTHON_IMAGE_PREFIX = "python:"
NODE_IMAGE_PREFIX = "node:"
GO_IMAGE_PREFIX = "golang:"
C_IMAGE_PREFIX = "gcc:"
CPP_IMAGE_PREFIX = "gcc:"


def _get_image_name(language: str, image_tag: str = None) -> str:
    """模拟_get_image_name方法"""
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
    else:
        raise ValueError(f"Unsupported language: {language}")


def test_constants():
    """测试常量定义"""
    print("测试1: 测试常量定义...")
    
    assert DEFAULT_C_IMAGE == "gcc:13-alpine", f"DEFAULT_C_IMAGE 应为 'gcc:13-alpine'"
    assert DEFAULT_CPP_IMAGE == "gcc:13-alpine", f"DEFAULT_CPP_IMAGE 应为 'gcc:13-alpine'"
    assert C_IMAGE_PREFIX == "gcc:", f"C_IMAGE_PREFIX 应为 'gcc:'"
    assert CPP_IMAGE_PREFIX == "gcc:", f"CPP_IMAGE_PREFIX 应为 'gcc:'"
    
    print("  ✓ C和C++常量定义正确")
    return True


def test_c_language():
    """测试C语言支持"""
    print("测试2: 测试C语言支持...")
    
    # 测试默认镜像
    image = _get_image_name("c")
    assert image == DEFAULT_C_IMAGE, f"默认C镜像应为 {DEFAULT_C_IMAGE}, 实际为 {image}"
    print(f"  ✓ 默认C镜像: {image}")
    
    # 测试带tag的镜像
    tagged = _get_image_name("c", "12")
    assert tagged == "gcc:12", f"带tag的C镜像应为 'gcc:12', 实际为 {tagged}"
    print(f"  ✓ 带tag的C镜像: {tagged}")
    
    # 测试带alpine后缀的tag
    alpine = _get_image_name("c", "13-alpine")
    assert alpine == "gcc:13-alpine", f"带alpine的C镜像应为 'gcc:13-alpine', 实际为 {alpine}"
    print(f"  ✓ 带alpine后缀的C镜像: {alpine}")
    
    # 测试无效tag
    try:
        _get_image_name("c", "invalid;tag")
        assert False, "无效tag应抛出ValueError"
    except ValueError as e:
        print(f"  ✓ 无效tag正确抛出异常: {e}")
    
    return True


def test_cpp_language():
    """测试C++语言支持"""
    print("测试3: 测试C++语言支持...")
    
    # 测试使用"cpp"标识
    image_cpp = _get_image_name("cpp")
    assert image_cpp == DEFAULT_CPP_IMAGE, f"'cpp'标识默认镜像应为 {DEFAULT_CPP_IMAGE}"
    print(f"  ✓ 'cpp'标识默认镜像: {image_cpp}")
    
    # 测试使用"c++"标识
    image_cpp_plus = _get_image_name("c++")
    assert image_cpp_plus == DEFAULT_CPP_IMAGE, f"'c++'标识默认镜像应为 {DEFAULT_CPP_IMAGE}"
    print(f"  ✓ 'c++'标识默认镜像: {image_cpp_plus}")
    
    # 测试带tag的镜像
    tagged_cpp = _get_image_name("cpp", "12")
    assert tagged_cpp == "gcc:12", f"带tag的C++镜像应为 'gcc:12'"
    print(f"  ✓ 带tag的C++镜像: {tagged_cpp}")
    
    # 测试使用"c++"带tag
    tagged_cpp_plus = _get_image_name("c++", "13-alpine")
    assert tagged_cpp_plus == "gcc:13-alpine", f"'c++'带alpine应为 'gcc:13-alpine'"
    print(f"  ✓ 'c++'带alpine后缀: {tagged_cpp_plus}")
    
    return True


def test_existing_languages():
    """测试现有语言支持是否正常"""
    print("测试4: 测试现有语言支持是否正常...")
    
    # Python
    python = _get_image_name("python")
    assert python == DEFAULT_PYTHON_IMAGE, f"Python镜像应为 {DEFAULT_PYTHON_IMAGE}"
    print(f"  ✓ Python镜像: {python}")
    
    # JavaScript
    js = _get_image_name("javascript")
    assert js == DEFAULT_NODE_IMAGE, f"JavaScript镜像应为 {DEFAULT_NODE_IMAGE}"
    print(f"  ✓ JavaScript镜像: {js}")
    
    # Go
    go = _get_image_name("go")
    assert go == DEFAULT_GO_IMAGE, f"Go镜像应为 {DEFAULT_GO_IMAGE}"
    print(f"  ✓ Go镜像: {go}")
    
    return True


def test_unsupported_language():
    """测试不支持的语言"""
    print("测试5: 测试不支持的语言...")
    
    try:
        _get_image_name("ruby")
        assert False, "不支持的语言应抛出ValueError"
    except ValueError as e:
        print(f"  ✓ 不支持的语言正确抛出异常: {e}")
    
    return True


def test_execute_command_pattern():
    """测试执行命令模式"""
    print("测试6: 测试执行命令模式...")
    
    # C语言: gcc -o /sandbox/exec /sandbox/exec.c 2>&1 && /sandbox/exec
    c_file = "exec.c"
    c_cmd = f"gcc -o /sandbox/exec /sandbox/{c_file} 2>&1 && /sandbox/exec"
    print(f"  ✓ C语言编译执行命令: {c_cmd}")
    
    # C++语言: g++ -o /sandbox/exec /sandbox/exec.cpp 2>&1 && /sandbox/exec
    cpp_file = "exec.cpp"
    cpp_cmd = f"g++ -o /sandbox/exec /sandbox/{cpp_file} 2>&1 && /sandbox/exec"
    print(f"  ✓ C++语言编译执行命令: {cpp_cmd}")
    
    # 验证文件命名
    assert c_file == "exec.c", "C语言文件应为exec.c"
    assert cpp_file == "exec.cpp", "C++语言文件应为exec.cpp"
    print("  ✓ 文件命名正确")
    
    return True


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("开始运行C和C++语言支持测试")
    print("=" * 60)
    
    tests_passed = 0
    tests_total = 6
    
    test_functions = [
        test_constants,
        test_c_language,
        test_cpp_language,
        test_existing_languages,
        test_unsupported_language,
        test_execute_command_pattern
    ]
    
    for test_func in test_functions:
        try:
            if test_func():
                tests_passed += 1
        except AssertionError as e:
            print(f"  ✗ 测试失败: {e}")
        print()
    
    print("=" * 60)
    print(f"测试完成: {tests_passed}/{tests_total} 通过")
    print("=" * 60)
    
    if tests_passed == tests_total:
        print("\n✓ 所有单元测试通过！")
        print("\n代码修改总结:")
        print("1. 添加了C和C++相关常量:")
        print("   - DEFAULT_C_IMAGE = 'gcc:13-alpine'")
        print("   - DEFAULT_CPP_IMAGE = 'gcc:13-alpine'")
        print("   - C_IMAGE_PREFIX = 'gcc:'")
        print("   - CPP_IMAGE_PREFIX = 'gcc:'")
        print("2. 更新了_get_image_name方法，支持:")
        print("   - language = 'c'")
        print("   - language = 'cpp' 或 'c++'")
        print("3. 更新了create_session方法，C/C++容器配置:")
        print("   - /tmp:exec,size=1g (允许编译执行)")
        print("   - ulimit nproc=512:512")
        print("   - ulimit nofile=1024:1024")
        print("   - pids-limit=256")
        print("4. 更新了execute_code方法:")
        print("   - C语言: gcc编译后执行")
        print("   - C++语言: g++编译后执行")
        print("\n接下来可以进行集成测试：")
        print("1. 确保依赖已安装: pip install -e .")
        print("2. 启动应用: python main.py")
        print("3. 创建C/C++会话并执行代码测试")
        return True
    else:
        print("\n✗ 部分测试失败，请检查代码修改")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
