#!/usr/bin/env python3
"""
🧪 管理助手 - ECC全面测试执行脚本

执行完整的ECC测试方案，包括：
- 单元测试
- 集成测试
- 代码覆盖率分析
- 详细报告生成

使用方法:
    python run_comprehensive_tests.py

作者: ECC测试方案
日期: 2026-03-05
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime
import platform


# 颜色输出
class Colors:
    """终端颜色"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def colorize(text: str, color: str) -> str:
    """为文本添加颜色"""
    if platform.system() == "Windows":
        return text
    return f"{color}{text}{Colors.ENDC}"


def print_banner():
    """打印横幅"""
    print()
    print(colorize("=" * 70, Colors.OKCYAN))
    print(colorize("🧪 管理助手 - ECC全面测试执行", Colors.BOLD + Colors.OKCYAN))
    print(colorize("=" * 70, Colors.OKCYAN))
    print(f"📅 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"💻 Python版本: {sys.version.split()[0]}")
    print(f"📁 工作目录: {Path.cwd()}")
    print()


def print_section(title: str):
    """打印章节标题"""
    print()
    print(colorize(f"{'=' * 70}", Colors.OKBLUE))
    print(colorize(f"🚀 {title}", Colors.BOLD + Colors.OKBLUE))
    print(colorize(f"{'=' * 70}", Colors.OKBLUE))
    print()


def run_unit_tests() -> int:
    """运行单元测试"""
    print_section("单元测试 (Unit Tests)")

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/unit",
        "-v",
        "--tb=short",
        "--cov=src",
        "--cov-report=term-missing:skip-covered",
        "-o",
        "console_output_style=progress",
    ]

    result = subprocess.run(cmd, capture_output=False)
    return result.returncode


def run_integration_tests() -> int:
    """运行集成测试"""
    print_section("集成测试 (Integration Tests)")

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/integration",
        "-v",
        "--tb=short",
        "--cov=src",
        "--cov-report=term-missing:skip-covered",
        "-o",
        "console_output_style=progress",
    ]

    result = subprocess.run(cmd, capture_output=False)
    return result.returncode


def generate_coverage_report():
    """生成覆盖率报告"""
    print_section("生成覆盖率报告")

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests",
        "--cov=src",
        "--cov-report=html",
        "--cov-report=xml",
        "--cov-report=term",
        "-q",
    ]

    subprocess.run(cmd, capture_output=True)


def print_summary(unit_exit: int, integration_exit: int):
    """打印摘要"""
    print()
    print(colorize("=" * 70, Colors.OKGREEN))
    print(colorize("📊 测试执行摘要", Colors.BOLD + Colors.OKGREEN))
    print(colorize("=" * 70, Colors.OKGREEN))
    print()

    # 计算总体状态
    total_exit = unit_exit + integration_exit

    if total_exit == 0:
        status = colorize("✅ 所有测试通过！", Colors.OKGREEN)
    else:
        status = colorize(f"❌ 部分测试失败 (单元:{unit_exit}, 集成:{integration_exit})", Colors.FAIL)

    print(f"🎯 测试状态: {status}")
    print()
    print("📈 覆盖率报告:")
    print(f"  {colorize('📄 HTML', Colors.OKCYAN)}: htmlcov/index.html")
    print(f"  {colorize('📄 XML', Colors.OKCYAN)}: coverage.xml")
    print()

    if total_exit == 0:
        print(colorize("🎉 恭喜！项目可以部署到生产环境！", Colors.BOLD + Colors.OKGREEN))
    else:
        print(colorize("⚠️  请修复失败的测试后再部署。", Colors.WARNING))

    print()


def main():
    """主函数"""
    print_banner()

    # 运行单元测试
    unit_exit = run_unit_tests()

    # 运行集成测试
    integration_exit = run_integration_tests()

    # 生成覆盖率报告
    generate_coverage_report()

    # 打印摘要
    print_summary(unit_exit, integration_exit)

    # 返回退出码
    return unit_exit + integration_exit


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
