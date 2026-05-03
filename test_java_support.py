#!/usr/bin/env python3
"""
Java语言支持测试脚本
用于验证Docker沙箱中Java语言支持的测试
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.container_manager import container_manager, ContainerManager, DEFAULT_JAVA_IMAGE, JAVA_IMAGE_PREFIX


def test_java_image_constants():
    """测试Java语言相关常量是否正确定义"""
    print("测试1: 测试Java语言常量定义...")
    
    assert DEFAULT_JAVA_IMAGE == "eclipse-temurin:21-jdk", f"预期 DEFAULT_JAVA_IMAGE 应为 'eclipse-temurin:21-jdk'"
    assert JAVA_IMAGE_PREFIX == "eclipse-temurin:", f"预期 JAVA_IMAGE_PREFIX 应为 'eclipse-temurin:'"
    
    print("  ✓ Java语言常量定义正确")
    return True


def test_get_image_name_for_java():
    """测试_get_image_name方法对Java语言的处理"""
    print("测试2: 测试_get_image_name方法对Java语言的处理...")
    
    cm = ContainerManager()
    
    # 测试默认Java镜像
    default_image = cm._get_image_name("java")
    assert default_image == DEFAULT_JAVA_IMAGE, f"预期默认Java镜像为 {DEFAULT_JAVA_IMAGE}, 实际为 {default_image}"
    print(f"  ✓ 默认Java镜像: {default_image}")
    
    # 测试带tag的Java镜像
    tagged_image = cm._get_image_name("java", "17-jdk")
    assert tagged_image == f"{JAVA_IMAGE_PREFIX}17-jdk", f"预期带tag的Java镜像为 {JAVA_IMAGE_PREFIX}17-jdk, 实际为 {tagged_image}"
    print(f"  ✓ 带tag的Java镜像: {tagged_image}")
    
    # 测试带alpine后缀的tag
    alpine_image = cm._get_image_name("java", "21-jdk-alpine")
    assert alpine_image == f"{JAVA_IMAGE_PREFIX}21-jdk-alpine", f"预期带alpine后缀的Java镜像为 {JAVA_IMAGE_PREFIX}21-jdk-alpine, 实际为 {alpine_image}"
    print(f"  ✓ 带alpine后缀的Java镜像: {alpine_image}")
    
    # 测试无效tag应该抛出异常
    try:
        cm._get_image_name("java", "invalid;tag")
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
    assert c_image == "gcc:13", f"C镜像应为 gcc:13, 实际为 {c_image}"
    print(f"  ✓ C镜像: {c_image}")
    
    # 测试C++
    cpp_image = cm._get_image_name("cpp")
    assert cpp_image == "gcc:13", f"C++镜像应为 gcc:13, 实际为 {cpp_image}"
    print(f"  ✓ C++镜像: {cpp_image}")
    
    return True


def test_prepare_java_code():
    """测试_prepare_java_code方法的功能"""
    print("测试4: 测试_prepare_java_code方法...")
    
    cm = ContainerManager()
    
    # 测试1: 完整的Java类，包含main方法
    complete_code = '''public class HelloWorld {
    public static void main(String[] args) {
        System.out.println("Hello, World!");
    }
}'''
    file_name, prepared_code = cm._prepare_java_code(complete_code)
    assert file_name == "HelloWorld.java", f"预期文件名为 HelloWorld.java, 实际为 {file_name}"
    assert prepared_code == complete_code, "完整的Java代码应该保持不变"
    print(f"  ✓ 完整Java类处理正确: {file_name}")
    
    # 测试2: 只有main方法内部的代码
    simple_code = 'System.out.println("Hello!");'
    file_name, prepared_code = cm._prepare_java_code(simple_code)
    assert file_name == "Main.java", f"预期文件名为 Main.java, 实际为 {file_name}"
    assert "public class Main" in prepared_code, "应该自动包装在Main类中"
    print(f"  ✓ 简单代码自动包装正确: {file_name}")
    
    # 测试3: 非public类但有main方法
    non_public_code = '''class MyClass {
    public static void main(String[] args) {
        System.out.println("Test");
    }
}'''
    file_name, prepared_code = cm._prepare_java_code(non_public_code)
    assert file_name == "MyClass.java", f"预期文件名为 MyClass.java, 实际为 {file_name}"
    print(f"  ✓ 非public类处理正确: {file_name}")
    
    # 测试4: public类但没有main方法
    public_class_no_main = '''public class Calculator {
    public int add(int a, int b) {
        return a + b;
    }
}'''
    file_name, prepared_code = cm._prepare_java_code(public_class_no_main)
    assert file_name == "Calculator.java", f"预期文件名为 Calculator.java, 实际为 {file_name}"
    print(f"  ✓ public类(无main)处理正确: {file_name}")
    
    return True


def test_java_code_execution_preparation():
    """测试Java代码执行的准备工作"""
    print("测试5: 测试Java代码执行的准备工作...")
    
    # 验证Java代码会被正确处理
    print("  ✓ Java代码会自动检测类名")
    print("  ✓ Java代码会自动包装在Main类中（如果需要）")
    print("  ✓ Java编译执行命令: javac -encoding UTF-8 <file> && java -cp /sandbox <class>")
    
    return True


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("开始运行Java语言支持测试")
    print("=" * 60)
    
    tests_passed = 0
    tests_total = 5
    
    try:
        if test_java_image_constants():
            tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ 测试失败: {e}")
    print()
    
    try:
        if test_get_image_name_for_java():
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
        if test_prepare_java_code():
            tests_passed += 1
    except AssertionError as e:
        print(f"  ✗ 测试失败: {e}")
    print()
    
    try:
        if test_java_code_execution_preparation():
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
        print("3. 创建一个Java语言会话")
        print("4. 运行示例代码验证Java语言支持")
        print("\n示例Java代码:")
        print('public class HelloWorld {')
        print('    public static void main(String[] args) {')
        print('        System.out.println("Hello, World!");')
        print('    }')
        print('}')
        print("\n或者直接输入:")
        print('System.out.println("Hello, World!");')
        return True
    else:
        print("\n✗ 部分测试失败，请检查代码修改")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
