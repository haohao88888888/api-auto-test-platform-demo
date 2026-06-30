import json

from runner.executor import load_cases, run_case, substitute_value


class DummyResponse:
    status_code = 500
    text = '{"code":0,"data":{"token":"bad-token"}}'

    def json(self):
        return {"code": 0, "data": {"token": "bad-token"}}


class DummySession:
    def request(self, **kwargs):
        return DummyResponse()


def test_substitute_value_replaces_variables_recursively():
    case = {
        "path": "/users/${user_id}",
        "headers": {"Authorization": "Bearer ${token}"},
        "params": [{"owner": "${user_id}"}],
        "json": {"user_id": "${user_id}", "active": "${active}"},
    }

    resolved = substitute_value(
        case,
        {"token": "demo-token-alice", "user_id": 1, "active": True},
    )

    assert resolved["path"] == "/users/1"
    assert resolved["headers"]["Authorization"] == "Bearer demo-token-alice"
    assert resolved["params"][0]["owner"] == 1
    assert resolved["json"]["user_id"] == 1
    assert resolved["json"]["active"] is True


def test_substitute_value_embedded_placeholder_becomes_string():
    resolved = substitute_value(
        {"header": "Bearer ${token}", "path": "/users/${user_id}"},
        {"token": "demo-token-alice", "user_id": 1},
    )

    assert resolved["header"] == "Bearer demo-token-alice"
    assert resolved["path"] == "/users/1"


def test_run_case_does_not_update_variables_when_assertion_fails():
    variables = {}
    case = {
        "id": "failed_login",
        "name": "Failed login must not publish token",
        "method": "POST",
        "path": "/login",
        "assertions": [{"type": "status_code", "expected": 200}],
        "extract": [{"name": "token", "path": "data.token"}],
    }

    result = run_case(DummySession(), "http://example.test", case, 5, variables)

    assert result["passed"] is False
    assert result["extracted"] == {"token": "bad-token"}
    assert variables == {}


def test_load_cases_rejects_empty_case_file(tmp_path):
    case_file = tmp_path / "empty.json"
    case_file.write_text(json.dumps({"cases": []}), encoding="utf-8")

    try:
        load_cases(case_file)
    except ValueError as exc:
        assert "at least one case" in str(exc)
    else:
        raise AssertionError("empty case file should be rejected")


def test_load_cases_rejects_unknown_assertion(tmp_path):
    payload = {
        "cases": [
            {
                "id": "bad_assertion",
                "method": "GET",
                "path": "/health",
                "assertions": [{"type": "not_supported"}],
            }
        ]
    }
    case_file = tmp_path / "bad.json"
    case_file.write_text(json.dumps(payload), encoding="utf-8")

    try:
        load_cases(case_file)
    except ValueError as exc:
        assert "unsupported assertion type" in str(exc)
    else:
        raise AssertionError("unknown assertion should be rejected")
