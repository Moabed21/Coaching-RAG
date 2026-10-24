from helpers.structured_data_helpers import get_employee_by_id, db
from .before_retrieval import get_remaining_budget

def validate_allowed_grade_courses(employee_id: str, recommended_courses: list[str]) -> list[str]:
    """
    Validates recommended courses against the employee's grade level.
    Returns only courses that the employee is eligible for (grade >= min_grade).
    """
    allowed = []
    e_grade = int(get_employee_by_id(employee_id)["grade"])
    catalog = db["catalog"]
    
    for course_id in recommended_courses:
        match = catalog[catalog["course_id"] == course_id]
        if not match.empty:
            min_grade = int(match.iloc[0]["min_grade"])
            if e_grade >= min_grade:
                allowed.append(course_id)
    return allowed

def validate_budget_limit_courses(employee_id: str, recommended_courses: list[str]) -> list[str]:
    """
    Validates recommended courses against the employee's remaining budget.
    Returns courses that fit within the remaining budget.
    """
    allowed = []
    remaining_budget = get_remaining_budget(employee_id)
    catalog = db["catalog"]
    
    for course_id in recommended_courses:
        match = catalog[catalog["course_id"] == course_id]
        if not match.empty:
            cost = int(match.iloc[0]["cost_qar"])
            if cost <= remaining_budget:
                allowed.append(course_id)
    return allowed

def filter_recommended_courses( candidate_courses: list[str], excluded_course_ids: set[str]) -> list[str]:
    """
    Final post-filter: takes retrieved candidates and removes any excluded courses,
    ensuring all recommendations are 100% policy-compliant.
    """
    valid_picks = [c for c in candidate_courses if c not in excluded_course_ids]
    return valid_picks

# for preventing the budget exceedence for the total recommended courses not each one individually(New Feature)
def filter_by_cumulative_budget(employee_id: str, candidate_courses: list[str], max_courses: int = 5) -> list[str]:
    """
    Accumulates course fees and selects candidates such that the total cost
    does not exceed the employee's remaining learning budget for 2026.
    """
    remaining_budget = get_remaining_budget(employee_id)
    catalog = db["catalog"]
    cost_map = dict(zip(catalog["course_id"], catalog["cost_qar"]))

    selected = []
    current_spent = 0

    for course_id in candidate_courses:
        cost = int(cost_map.get(course_id, 0))
        if current_spent + cost <= remaining_budget:
            selected.append(course_id)
            current_spent += cost
            if len(selected) >= max_courses:
                break

    return selected

# for handling cases where policy is relevant to the question(New Feature)
def is_policy_question(question: str) -> bool:
    """Detects if question asks about company rules, approvals, or degree sponsorship."""
    q_lower = question.lower()
    policy_terms = ["approval", "sponsor", "mba", "policy", "study leave", "carry over", "rollover"]
    coaching_terms = ["which", "what should i learn", "what to study", "what training", "ما الدورات"]
    return any(p in q_lower for p in policy_terms) and not any(c in q_lower for c in coaching_terms)
