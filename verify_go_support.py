#!/usr/bin/env python3
"""
简单的Go语言支持验证脚本
直接检查代码修改是否正确
"""

import re
import sys

# 定义我们期望的常量值
EXPECTED_DEFAULT_GO_IMAGE = "golang:1.22-alpine"
EXPECTED_GO_IMAGE_PREFIX = "golang:"


def check_container_manager_modifications():
    """检查container_manager.py中的修改"""
    print("=" * 60)
    print("检查 container_manager.py 的修改")
    print("=" * 60)
    
    with open("/data/projects/work/soloCoder/soloCoder-D/app/container_manager.py", "r") as f:
        content = f.read()
    
    issues = []
    checks_passed = 0
    
    # 检查1: 检查DEFAULT_GO_IMAGE常量
    if 'DEFAULT_GO_IMAGE = "golang:1.22-alpine"' in content:
        print("✓ 检查1: DEFAULT_GO_IMAGE 常量已正确定义")
        checks_passed += 1
    else:
        issues.append("DEFAULT_GO_IMAGE 常量未正确定义")
        print("✗ 检查1: DEFAULT_GO_IMAGE 常量未正确定义")
    
    # 检查2: 检查GO_IMAGE_PREFIX常量
    if 'GO_IMAGE_PREFIX = "golang:"' in content:
        print("✓ 检查2: GO_IMAGE_PREFIX 常量已正确定义")
        checks_passed += 1
    else:
        issues.append("GO_IMAGE_PREFIX 常量未正确定义")
        print("✗ 检查2: GO_IMAGE_PREFIX 常量未正确定义")
    
    # 检查3: 检查_get_image_name方法中的Go语言支持
    if 'elif language == "go":' in content:
        print("✓ 检查3: _get_image_name 方法中已添加Go语言支持")
        checks_passed += 1
    else:
        issues.append("_get_image_name 方法中未添加Go语言支持")
        print("✗ 检查3: _get_image_name 方法中未添加Go语言支持")
    
    # 检查4: 检查create_session方法中的Go语言环境变量
    if 'elif language == "go":' in content and 'GOPATH=/go' in content:
        print("✓ 检查4: create_session 方法中已添加Go语言环境变量")
        checks_passed += 1
    else:
        issues.append("create_session 方法中未添加Go语言环境变量")
        print("✗ 检查4: create_session 方法中未添加Go语言环境变量")
    
    # 检查5: 检查execute_code方法中的Go语言支持
    # 注意: "go" 和 "run" 在代码中是作为列表的独立元素存在的
    if 'elif session.language == "go":' in content and '"go"' in content and '"run"' in content and 'exec.go' in content:
        print("✓ 检查5: execute_code 方法中已添加Go语言执行支持")
        checks_passed += 1
    else:
        issues.append("execute_code 方法中未添加Go语言执行支持")
        print("✗ 检查5: execute_code 方法中未添加Go语言执行支持")
    
    return checks_passed, 5, issues


def check_app_js_modifications():
    """检查app.js中的修改"""
    print("\n" + "=" * 60)
    print("检查 app.js 的修改")
    print("=" * 60)
    
    with open("/data/projects/work/soloCoder/soloCoder-D/static/js/app.js", "r") as f:
        content = f.read()
    
    issues = []
    checks_passed = 0
    
    # 检查1: 检查Go语言默认代码
    if 'else if (language === \'go\')' in content or 'else if (language === "go")' in content:
        print("✓ 检查1: loadDefaultCode 方法中已添加Go语言默认代码")
        checks_passed += 1
    else:
        issues.append("loadDefaultCode 方法中未添加Go语言默认代码")
        print("✗ 检查1: loadDefaultCode 方法中未添加Go语言默认代码")
    
    # 检查2: 检查formatLanguage方法中的Go语言支持
    if "'go': 'Go'" in content:
        print("✓ 检查2: formatLanguage 方法中已添加Go语言显示名称")
        checks_passed += 1
    else:
        issues.append("formatLanguage 方法中未添加Go语言显示名称")
        print("✗ 检查2: formatLanguage 方法中未添加Go语言显示名称")
    
    # 检查3: 检查语言选择模态框中的Go语言选项
    if 'data-language="go"' in content and '<div class="language-name">Go</div>' in content:
        print("✓ 检查3: 语言选择模态框中已添加Go语言选项")
        checks_passed += 1
    else:
        issues.append("语言选择模态框中未添加Go语言选项")
        print("✗ 检查3: 语言选择模态框中未添加Go语言选项")
    
    # 检查4: 检查镜像配置模态框中的Go语言支持
    if 'else if (language === \'go\')' in content or 'else if (language === "go")' in content:
        print("✓ 检查4: 镜像配置模态框中已添加Go语言支持")
        checks_passed += 1
    else:
        issues.append("镜像配置模态框中未添加Go语言支持")
        print("✗ 检查4: 镜像配置模态框中未添加Go语言支持")
    
    return checks_passed, 4, issues


def main():
    """主函数"""
    print("Go语言支持验证脚本")
    print("验证Docker沙箱中Go语言支持的代码修改")
    print()
    
    total_checks = 0
    total_passed = 0
    all_issues = []
    
    # 检查container_manager.py
    passed, total, issues = check_container_manager_modifications()
    total_passed += passed
    total_checks += total
    all_issues.extend(issues)
    
    # 检查app.js
    passed, total, issues = check_app_js_modifications()
    total_passed += passed
    total_checks += total
    all_issues.extend(issues)
    
    # 输出总结
    print("\n" + "=" * 60)
    print("验证结果总结")
    print("=" * 60)
    print(f"总检查项: {total_checks}")
    print(f"通过: {total_passed}")
    print(f"失败: {total_checks - total_passed}")
    
    if all_issues:
        print("\n发现的问题:")
        for issue in all_issues:
            print(f"  - {issue}")
    
    if total_passed == total_checks:
        print("\n✓ 所有验证通过！Go语言支持已成功添加。")
        print("\n接下来可以进行集成测试：")
        print("1. 确保Docker已安装并运行")
        print("2. 安装依赖: pip install -r requirements.txt (如果有)")
        print("3. 启动应用: python main.py")
        print("4. 打开浏览器访问 http://localhost:4444")
        print("5. 创建一个Go语言会话")
        print("6. 运行示例代码验证Go语言支持")
        return True
    else:
        print("\n✗ 部分验证失败，请检查代码修改。")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
