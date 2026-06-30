import json

from runner.report import write_reports
from runner.redaction import redact_result


def test_redact_result_masks_auth_token_and_contact_data():
    result = {
        "url": "http://example.test/orders?token=demo-token&email=alice@example.com",
        "headers": {"Authorization": "Bearer demo-token-alice"},
        "extracted": {"token": "demo-token-alice"},
        "error": "phone 13812345678",
    }

    redacted = redact_result(result)

    assert "demo-token-alice" not in json.dumps(redacted)
    assert "alice@example.com" not in json.dumps(redacted)
    assert "13812345678" not in json.dumps(redacted)
    assert redacted["extracted"]["token"] == "[REDACTED]"


def test_write_reports_persists_redacted_json(tmp_path):
    results = [
        {
            "id": "login_success",
            "name": "Login",
            "method": "POST",
            "url": "http://example.test/login",
            "status_code": 200,
            "elapsed_ms": 1.0,
            "passed": True,
            "skipped": False,
            "checks": [],
            "extracted": {"token": "demo-token-alice"},
            "error": None,
        }
    ]

    report = write_reports(results, tmp_path)
    payload = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))

    assert payload["results"][0]["extracted"]["token"] == "[REDACTED]"
    assert "demo-token-alice" not in (tmp_path / "report.html").read_text(encoding="utf-8")
    assert report["summary"]["passed"] == 1
