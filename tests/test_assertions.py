from runner.assertions import evaluate_assertion, resolve_json_path


class DummyResponse:
    status_code = 200
    text = '{"code":0,"data":{"items":[{"name":"Keyboard"}]}}'

    def json(self):
        return {"code": 0, "data": {"items": [{"name": "Keyboard"}]}}


def test_resolve_json_path_supports_nested_list_indexes():
    data = {"data": {"items": [{"name": "Keyboard"}]}}

    assert resolve_json_path(data, "data.items.0.name") == "Keyboard"


def test_status_code_assertion_records_pass_message():
    result = evaluate_assertion(
        DummyResponse(),
        12.5,
        {"type": "status_code", "expected": 200},
    )

    assert result["passed"] is True
    assert "200" in result["message"]


def test_json_equals_assertion_reports_mismatch():
    result = evaluate_assertion(
        DummyResponse(),
        12.5,
        {"type": "json_equals", "path": "code", "expected": 1},
    )

    assert result["passed"] is False
    assert "expected 1" in result["message"]
