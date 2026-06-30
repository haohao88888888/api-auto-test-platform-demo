import html
import json
from pathlib import Path

from runner.redaction import redact_results, redact_text


def build_summary(results):
    total = len(results)
    passed = sum(1 for item in results if item["passed"])
    skipped = sum(1 for item in results if item.get("skipped"))
    failed = total - passed - skipped
    pass_rate = round((passed / total) * 100, 2) if total else 0
    avg_elapsed_ms = (
        round(sum(item.get("elapsed_ms", 0) for item in results) / total, 2)
        if total
        else 0
    )
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "pass_rate": pass_rate,
        "avg_elapsed_ms": avg_elapsed_ms,
    }


def check_messages(result):
    if result.get("error"):
        return html.escape(redact_text(result["error"]))

    messages = []
    for check in result.get("checks", []):
        status = "PASS" if check["passed"] else "FAIL"
        message = html.escape(redact_text(check["message"]))
        messages.append(f"[{status}] {html.escape(check['type'])}: {message}")
    for name, value in result.get("extracted", {}).items():
        messages.append(
            f"[EXTRACTED] {html.escape(name)}={html.escape(redact_text(value))}"
        )
    return "<br>".join(messages)


def build_html(results, summary):
    rows = []
    for result in results:
        if result.get("skipped"):
            status = "SKIP"
            css_class = "skipped"
        else:
            status = "PASS" if result["passed"] else "FAIL"
            css_class = "passed" if result["passed"] else "failed"
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(result.get('id')))}</td>"
            f"<td>{html.escape(str(result.get('name')))}</td>"
            f"<td>{html.escape(result.get('method') or '')}</td>"
            f"<td>{html.escape(result.get('url') or '')}</td>"
            f"<td>{result.get('status_code')}</td>"
            f"<td>{result.get('elapsed_ms')} ms</td>"
            f"<td class='{css_class}'>{status}</td>"
            f"<td>{check_messages(result)}</td>"
            "</tr>"
        )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>API Test Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; color: #222; }}
    h1 {{ margin-bottom: 8px; }}
    .summary {{ margin: 12px 0 20px; }}
    .summary span {{ display: inline-block; margin-right: 18px; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 14px; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; vertical-align: top; }}
    th {{ background: #f5f5f5; text-align: left; }}
    .passed {{ color: #157347; font-weight: bold; }}
    .failed {{ color: #b02a37; font-weight: bold; }}
    .skipped {{ color: #6c757d; font-weight: bold; }}
  </style>
</head>
<body>
  <h1>API Test Report</h1>
  <div class="summary">
    <span>Total: {summary['total']}</span>
    <span>Passed: {summary['passed']}</span>
    <span>Failed: {summary['failed']}</span>
    <span>Skipped: {summary['skipped']}</span>
    <span>Pass rate: {summary['pass_rate']}%</span>
    <span>Avg elapsed: {summary['avg_elapsed_ms']} ms</span>
  </div>
  <table>
    <thead>
      <tr>
        <th>ID</th>
        <th>Name</th>
        <th>Method</th>
        <th>URL</th>
        <th>Status</th>
        <th>Elapsed</th>
        <th>Result</th>
        <th>Checks</th>
      </tr>
    </thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
</body>
</html>
"""


def write_reports(results, report_dir):
    output_dir = Path(report_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_results = redact_results(results)
    summary = build_summary(results)
    payload = {"summary": summary, "results": safe_results}

    json_path = output_dir / "report.json"
    html_path = output_dir / "report.html"

    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    html_path.write_text(build_html(safe_results, summary), encoding="utf-8")

    return {"summary": summary, "json": str(json_path), "html": str(html_path)}
