import argparse
from pathlib import Path

from runner.executor import run_cases
from runner.report import write_reports


ROOT = Path(__file__).resolve().parent


def parse_args():
    parser = argparse.ArgumentParser(description="Run API automation test cases.")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8001",
        help="Base URL of the API service.",
    )
    parser.add_argument(
        "--cases",
        default=str(ROOT / "cases" / "api_cases.json"),
        help="JSON case file path.",
    )
    parser.add_argument(
        "--report-dir",
        default=str(ROOT / "reports"),
        help="Report output directory.",
    )
    parser.add_argument("--timeout", type=float, default=5, help="Request timeout.")
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        results = run_cases(args.cases, args.base_url, timeout=args.timeout)
    except ValueError as exc:
        print(f"Invalid case file: {exc}")
        return 2

    report = write_reports(results, args.report_dir)
    summary = report["summary"]

    print(
        "API test completed: "
        f"total={summary['total']}, "
        f"passed={summary['passed']}, "
        f"failed={summary['failed']}, "
        f"skipped={summary['skipped']}, "
        f"pass_rate={summary['pass_rate']}%"
    )
    print(f"HTML report: {report['html']}")
    print(f"JSON report: {report['json']}")

    return 0 if summary["passed"] == summary["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
