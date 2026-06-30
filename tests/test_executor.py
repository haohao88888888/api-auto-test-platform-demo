import json

from runner.executor import load_cases, substitute_value


def test_substitute_value_replaces_variables_recursively():
    case = {
        "path": "/users/${user_id}",
        "headers": {"Authorization": "Bearer ${token}"},
        "params": [{"owner": "${user_id}"}],
    }

    resolved = substitute_value(case, {"token": "demo-token-alice", "user_id": 1})

    assert resolved["path"] == "/users/1"
    assert resolved["headers"]["Authorization"] == "Bearer demo-token-alice"
    assert resolved["params"][0]["owner"] == "1"


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
