import json
import re
import time
from pathlib import Path

import requests

from runner.assertions import evaluate_assertion, resolve_json_path, response_json
from runner.schema import validate_cases


VARIABLE_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def load_cases(case_file):
    with open(case_file, "r", encoding="utf-8") as file:
        payload = json.load(file)

    return validate_cases(payload)


def build_url(base_url, path):
    return f"{base_url.rstrip('/')}/{str(path).lstrip('/')}"


def substitute_value(value, variables):
    if isinstance(value, str):
        def replace(match):
            name = match.group(1)
            if name not in variables:
                raise KeyError(f"variable {name!r} was not extracted")
            return str(variables[name])

        return VARIABLE_PATTERN.sub(replace, value)

    if isinstance(value, list):
        return [substitute_value(item, variables) for item in value]

    if isinstance(value, dict):
        return {key: substitute_value(item, variables) for key, item in value.items()}

    return value


def extract_variables(response, extractors):
    if not extractors:
        return {}, []

    data = response_json(response)
    extracted = {}
    checks = []

    for extractor in extractors:
        name = extractor["name"]
        path = extractor["path"]
        try:
            value = resolve_json_path(data, path)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            checks.append(
                {
                    "type": "extract",
                    "passed": False,
                    "message": f"failed to extract {name} from {path!r}: {exc}",
                }
            )
            continue

        extracted[name] = value
        checks.append(
            {
                "type": "extract",
                "passed": True,
                "message": f"extracted {name} from {path!r}",
            }
        )

    return extracted, checks


def normalize_dependencies(case):
    depends_on = case.get("depends_on", [])
    if isinstance(depends_on, str):
        return [depends_on]
    return depends_on


def build_skipped_result(case, dependency):
    return {
        "id": case.get("id"),
        "name": case.get("name"),
        "method": str(case.get("method", "GET")).upper(),
        "url": None,
        "status_code": None,
        "elapsed_ms": 0,
        "passed": False,
        "skipped": True,
        "checks": [],
        "extracted": {},
        "error": f"skipped because dependency {dependency!r} did not pass",
    }


def run_case(session, base_url, case, timeout, variables):
    method = str(case.get("method", "GET")).upper()
    url = None
    started_at = time.perf_counter()

    try:
        prepared_case = substitute_value(case, variables)
        method = str(prepared_case.get("method", "GET")).upper()
        url = build_url(base_url, prepared_case.get("path", ""))
        response = session.request(
            method=method,
            url=url,
            headers=prepared_case.get("headers") or {},
            params=prepared_case.get("params") or {},
            json=prepared_case.get("json"),
            timeout=timeout,
        )
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        checks = [
            evaluate_assertion(response, elapsed_ms, assertion)
            for assertion in prepared_case.get("assertions", [])
        ]
        extracted, extract_checks = extract_variables(
            response,
            prepared_case.get("extract", []),
        )
        checks.extend(extract_checks)
        variables.update(extracted)
        passed = all(check["passed"] for check in checks)

        return {
            "id": case.get("id"),
            "name": case.get("name"),
            "method": method,
            "url": url,
            "status_code": response.status_code,
            "elapsed_ms": round(elapsed_ms, 2),
            "passed": passed,
            "skipped": False,
            "checks": checks,
            "extracted": extracted,
            "error": None,
        }
    except (requests.RequestException, KeyError, ValueError) as exc:
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        return {
            "id": case.get("id"),
            "name": case.get("name"),
            "method": method,
            "url": url,
            "status_code": None,
            "elapsed_ms": round(elapsed_ms, 2),
            "passed": False,
            "skipped": False,
            "checks": [],
            "extracted": {},
            "error": str(exc),
        }


def run_cases(case_file, base_url, timeout=5):
    cases = load_cases(Path(case_file))
    variables = {}
    results = []
    results_by_id = {}

    with requests.Session() as session:
        for case in cases:
            failed_dependency = next(
                (
                    dependency
                    for dependency in normalize_dependencies(case)
                    if not results_by_id.get(dependency, {}).get("passed", False)
                ),
                None,
            )
            if failed_dependency is not None:
                result = build_skipped_result(case, failed_dependency)
            else:
                result = run_case(session, base_url, case, timeout, variables)

            results.append(result)
            results_by_id[result["id"]] = result

    return results
