#!/usr/bin/env python3
"""Run the complete MoneyPrinterTurbo automated test suite.

Default mode is offline/safe: provider-backed integration tests remain skipped
unless MPT_RUN_INTEGRATION_TESTS=1 is explicitly supplied or --integration is used.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--integration", action="store_true",
        help="enable tests that may contact external LLM/TTS providers",
    )
    parser.add_argument(
        "--coverage", action="store_true",
        help="run pytest under coverage and print a coverage report",
    )
    parser.add_argument(
        "--junitxml", metavar="PATH",
        help="write a JUnit XML report to PATH",
    )
    parser.add_argument(
        "-k", dest="keyword", metavar="EXPR",
        help="run only tests matching a pytest -k expression",
    )
    args = parser.parse_args()

    if not (ROOT / "test").is_dir():
        print("ERROR: test/ directory not found.", file=sys.stderr)
        return 2

    env = os.environ.copy()
    if args.integration:
        env["MPT_RUN_INTEGRATION_TESTS"] = "1"

    targets = ["test"]
    if (ROOT / "tests").is_dir():
        targets.append("tests")

    pytest_args = ["-q", "--disable-warnings", *targets]
    if args.keyword:
        pytest_args.extend(["-k", args.keyword])
    if args.junitxml:
        report = Path(args.junitxml).expanduser()
        if not report.is_absolute():
            report = ROOT / report
        report.parent.mkdir(parents=True, exist_ok=True)
        pytest_args.append(f"--junitxml={report}")

    if args.coverage:
        if shutil.which("coverage") is None:
            print("ERROR: coverage is not installed. Install it with: uv add --dev coverage",
                  file=sys.stderr)
            return 2
        command = [sys.executable, "-m", "coverage", "run", "--source=app", "-m",
                   "pytest", *pytest_args]
    else:
        command = [sys.executable, "-m", "pytest", *pytest_args]

    print("=" * 72)
    print("MoneyPrinterTurbo — COMPLETE AUTOMATED TEST SUITE")
    print(f"Repository: {ROOT}")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Integration tests: {'ENABLED' if env.get('MPT_RUN_INTEGRATION_TESTS') == '1' else 'disabled'}")
    print(f"Targets: {', '.join(targets)}")
    print("=" * 72, flush=True)

    result = subprocess.run(command, cwd=ROOT, env=env, check=False)
    if args.coverage:
        report_result = subprocess.run(
            [sys.executable, "-m", "coverage", "report", "-m"],
            cwd=ROOT, env=env, check=False,
        )
        if result.returncode == 0 and report_result.returncode:
            return report_result.returncode

    if result.returncode:
        print("\nRESULT: FAILED — inspect the pytest failure summary above.")
        return result.returncode
    print("\nRESULT: PASSED — all collected tests completed successfully.")
    if not args.integration:
        print("NOTE: provider-backed integration tests were not enabled.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
