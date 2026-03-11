"""Test runner script for Management Assistant project."""

import sys
import subprocess
from pathlib import Path


def run_tests():
    """Run all tests with coverage."""
    project_root = Path(__file__).parent

    # Run pytest with coverage
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests",
        "-v",
        "--tb=short",
        "--cov=src",
        "--cov-report=term-missing",
        "--cov-report=html",
        "--cov-report=xml",
        "-o",
        "console_output_style=progress",
    ]

    print("Running tests...")
    print("Command:", " ".join(cmd))
    print()

    result = subprocess.run(cmd, cwd=project_root, capture_output=False)

    # Generate summary
    print("\n" + "=" * 60)
    print("Test Execution Summary")
    print("=" * 60)

    if result.returncode == 0:
        print("✅ All tests passed!")
    else:
        print(f"❌ Some tests failed (exit code: {result.returncode})")

    print()
    print("Coverage report generated:")
    print(f"  - HTML: {project_root / 'htmlcov' / 'index.html'}")
    print(f"  - XML: {project_root / 'coverage.xml'}")

    return result.returncode


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
