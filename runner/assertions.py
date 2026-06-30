def resolve_json_path(data, path):
    if path in (None, ""):
        return data

    current = data
    for part in str(path).split("."):
        if isinstance(current, list):
            index = int(part)
            current = current[index]
        elif isinstance(current, dict):
            if part not in current:
                raise KeyError(part)
            current = current[part]
        else:
            raise KeyError(part)
    return current


def response_json(response):
    try:
        return response.json()
    except ValueError:
        return None


def pass_result(assertion_type, message):
    return {"type": assertion_type, "passed": True, "message": message}


def fail_result(assertion_type, message):
    return {"type": assertion_type, "passed": False, "message": message}


def evaluate_assertion(response, elapsed_ms, assertion):
    assertion_type = assertion.get("type")

    if assertion_type == "status_code":
        expected = assertion.get("expected")
        actual = response.status_code
        if actual == expected:
            return pass_result(assertion_type, f"status_code == {expected}")
        return fail_result(assertion_type, f"expected {expected}, got {actual}")

    if assertion_type == "response_time_lt_ms":
        expected = assertion.get("expected")
        if elapsed_ms < expected:
            return pass_result(
                assertion_type,
                f"response_time {elapsed_ms:.1f}ms < {expected}ms",
            )
        return fail_result(
            assertion_type,
            f"expected < {expected}ms, got {elapsed_ms:.1f}ms",
        )

    if assertion_type == "text_contains":
        expected = str(assertion.get("expected", ""))
        if expected in response.text:
            return pass_result(assertion_type, f"text contains {expected!r}")
        return fail_result(assertion_type, f"text does not contain {expected!r}")

    data = response_json(response)
    if data is None:
        return fail_result(assertion_type, "response is not valid JSON")

    path = assertion.get("path")
    try:
        actual = resolve_json_path(data, path)
    except (KeyError, IndexError, ValueError) as exc:
        return fail_result(assertion_type, f"json path {path!r} not found: {exc}")

    if assertion_type == "json_exists":
        return pass_result(assertion_type, f"json path {path!r} exists")

    if assertion_type == "json_equals":
        expected = assertion.get("expected")
        if actual == expected:
            return pass_result(assertion_type, f"{path} == {expected!r}")
        return fail_result(
            assertion_type,
            f"{path} expected {expected!r}, got {actual!r}",
        )

    if assertion_type == "json_contains":
        expected = str(assertion.get("expected", ""))
        if expected in str(actual):
            return pass_result(assertion_type, f"{path} contains {expected!r}")
        return fail_result(
            assertion_type,
            f"{path} does not contain {expected!r}, actual {actual!r}",
        )

    return fail_result(assertion_type or "unknown", "unknown assertion type")
