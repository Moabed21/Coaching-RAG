import json
import re
import sys
from pathlib import Path
from main import get_employee_id_and_question, extract_target_employee, check_privacy_access
from helpers import db

DEV_SET_PATH = Path("data/eval/dev_set.jsonl")


def load_dev_set():
    cases = []
    with open(DEV_SET_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                cases.append(json.loads(line.strip()))
    return cases


def get_course_cost(course_id: str) -> int:
    catalog = db["catalog"]
    row = catalog[catalog["course_id"] == course_id]
    if not row.empty:
        try:
            return int(row.iloc[0]["cost_qar"])
        except (ValueError, TypeError):
            return 0
    return 0


def evaluate_case(case: dict) -> dict:
    asker_id = case["asker"]
    question = case["input"]
    expected_behavior = case.get("expected_behavior", "answer")

    # Run system
    response = get_employee_id_and_question(asker_id, question)
    errors = []

    # 1. Check expected behavior
    if expected_behavior == "decline":
        target_id = extract_target_employee(asker_id, question)
        if check_privacy_access(asker_id, target_id):
            errors.append("Privacy check failed: unauthorized request was not declined.")
    elif expected_behavior == "say_not_in_documents":
        resp_clean = response.lower().replace("’", "'")
        valid_fallback = any(phrase in resp_clean for phrase in [
            "couldn't find that in the documents",
            "could not find that in the documents",
            "couldn't find any information",
            "could not find any information",
            "not covered in the documents"
        ])
        if not valid_fallback:
            errors.append("Missing required out-of-scope fallback statement.")

    # 2. Check forbidden items (must_not)
    must_not_courses = [c for c in case.get("must_not", []) if re.match(r"^LD-\d{3}$", c)]
    violations = [c for c in must_not_courses if c in response]
    if violations:
        errors.append(f"Recommended forbidden course(s): {', '.join(violations)}")

    # 3. Check required mandatory courses
    required_mandatory = case.get("required_mandatory", [])
    for m in required_mandatory:
        if m not in response:
            errors.append(f"Missing required mandatory course: {m}")

    # 4. Extract recommended courses and check budget & order
    found_courses = list(dict.fromkeys(re.findall(r"LD-\d{3}", response)))
    optional_courses = [c for c in found_courses if c not in required_mandatory]

    # Mandatory courses must appear before optional courses
    for m in required_mandatory:
        m_pos = response.find(m)
        for opt in optional_courses:
            if response.find(opt) < m_pos:
                errors.append(f"Mandatory course {m} is not listed before optional course {opt}")
                break

    # Budget check
    remaining_budget = case.get("budget_remaining_qar")
    if remaining_budget is not None:
        total_optional_cost = sum(get_course_cost(c) for c in optional_courses)
        if total_optional_cost > remaining_budget:
            errors.append(f"Total optional cost QAR {total_optional_cost} exceeds remaining budget QAR {remaining_budget}")

    # 5. Language check
    if case.get("language") == "ar":
        if not re.search(r"[\u0600-\u06FF]", response):
            errors.append("Expected Arabic response, but output has no Arabic text.")

    return {
        "id": case["id"],
        "category": case.get("category"),
        "passed": len(errors) == 0,
        "errors": errors,
        "response": response
    }


def run_tests(case_id: str = None):
    cases = load_dev_set()
    if case_id:
        cases = [c for c in cases if c["id"].upper() == case_id.upper()]

    print(f"\nEvaluating {len(cases)} test cases...\n")
    passed_count = 0

    for case in cases:
        cid = case["id"]
        res = evaluate_case(case)
        status = "PASS" if res["passed"] else "FAIL"

        print(f"[{status}] {cid} ({case.get('category')})")
        if not res["passed"]:
            for err in res["errors"]:
                print(f"   -> {err}")
        else:
            passed_count += 1

    print(f"\nResult: {passed_count}/{len(cases)} passed ({(passed_count/len(cases))*100:.1f}%)\n")


if __name__ == "__main__":
    target_case = sys.argv[1] if len(sys.argv) > 1 else None
    run_tests(target_case)
