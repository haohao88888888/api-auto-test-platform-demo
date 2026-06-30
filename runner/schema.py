ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}

ALLOWED_ASSERTIONS = {
    "status_code",
    "response_time_lt_ms",
    "text_contains",
    "json_exists",
    "json_equals",
    "json_contains",
}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _case_label(case, index):
    return case.get("id") or case.get("name") or f"case[{index}]"


def _require_string(value, message):
    _require(isinstance(value, str) and value.strip(), message)


def _validate_assertion(label, assertion, assertion_index):
    _require(isinstance(assertion, dict), f"{label}: assertion[{assertion_index}] must be an object")
    assertion_type = assertion.get("type")
    _require(
        assertion_type in ALLOWED_ASSERTIONS,
        f"{label}: unsupported assertion type {assertion_type!r}",
    )

    prefix = f"{label}: assertion[{assertion_index}] {assertion_type}"
    if assertion_type == "status_code":
        _require(isinstance(assertion.get("expected"), int), f"{prefix}: expected integer is required")
    elif assertion_type == "response_time_lt_ms":
        expected = assertion.get("expected")
        _require(
            isinstance(expected, (int, float)) and expected > 0,
            f"{prefix}: positive expected number is required",
        )
    elif assertion_type == "text_contains":
        _require_string(assertion.get("expected"), f"{prefix}: expected text is required")
    elif assertion_type == "json_exists":
        _require_string(assertion.get("path"), f"{prefix}: path is required")
    elif assertion_type in {"json_equals", "json_contains"}:
        _require_string(assertion.get("path"), f"{prefix}: path is required")
        _require("expected" in assertion, f"{prefix}: expected is required")


def _validate_object_field(case, field_name, label):
    if field_name in case and case[field_name] is not None:
        _require(isinstance(case[field_name], dict), f"{label}: {field_name} must be an object")


def validate_cases(payload):
    cases = payload.get("cases", []) if isinstance(payload, dict) else payload
    _require(isinstance(cases, list), "case file must be a JSON list or contain a cases list")
    _require(cases, "case file must contain at least one case")

    seen_ids = set()
    for index, case in enumerate(cases):
        label = _case_label(case, index) if isinstance(case, dict) else f"case[{index}]"
        _require(isinstance(case, dict), f"{label}: case must be an object")

        case_id = case.get("id")
        _require(isinstance(case_id, str) and case_id.strip(), f"{label}: id is required")
        _require(case_id not in seen_ids, f"{label}: duplicate case id")

        method = str(case.get("method", "GET")).upper()
        _require(method in ALLOWED_METHODS, f"{label}: unsupported method {method!r}")
        _require_string(case.get("path"), f"{label}: path is required")
        _validate_object_field(case, "headers", label)
        _validate_object_field(case, "params", label)

        assertions = case.get("assertions")
        _require(isinstance(assertions, list) and assertions, f"{label}: assertions must be a non-empty list")
        for assertion_index, assertion in enumerate(assertions):
            _validate_assertion(label, assertion, assertion_index)

        extractors = case.get("extract", [])
        _require(isinstance(extractors, list), f"{label}: extract must be a list")
        for extractor_index, extractor in enumerate(extractors):
            _require(isinstance(extractor, dict), f"{label}: extract[{extractor_index}] must be an object")
            _require(
                isinstance(extractor.get("name"), str) and extractor["name"].strip(),
                f"{label}: extract[{extractor_index}].name is required",
            )
            _require(
                isinstance(extractor.get("path"), str) and extractor["path"].strip(),
                f"{label}: extract[{extractor_index}].path is required",
            )

        depends_on = case.get("depends_on", [])
        if isinstance(depends_on, str):
            depends_on = [depends_on]
        _require(isinstance(depends_on, list), f"{label}: depends_on must be a string or list")
        for dependency in depends_on:
            _require(isinstance(dependency, str) and dependency.strip(), f"{label}: dependency id must be a string")
            _require(
                dependency in seen_ids,
                f"{label}: dependency {dependency!r} must reference an earlier case id",
            )

        seen_ids.add(case_id)

    return cases
