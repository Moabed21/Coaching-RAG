from helpers.structured_data_helpers import get_employee_by_id, db
from .before_retrieval import get_remaining_budget
from agent import few_shot_caller

CLASSIFICATION_EXAMPLES = [
    {"role": "user", "content": "What courses should I take to grow in maintenance?"},
    {"role": "assistant", "content": "coaching"},
    {"role": "user", "content": "I still have some training budget left this year. What's the best use of it?"},
    {"role": "assistant", "content": "coaching"},
    {"role": "user", "content": "Do I need approval for a 4000 QAR course?"},
    {"role": "assistant", "content": "policy"},
    {"role": "user", "content": "هل الشركة ترعى دراسة الماجستير؟"},
    {"role": "assistant", "content": "general"},
    {"role": "user", "content": "Will the company sponsor me to do an MBA?"},
    {"role": "assistant", "content": "general"},
    {"role": "user", "content": "ما الدورات المناسبة لتطوير مهاراتي؟"},
    {"role": "assistant", "content": "coaching"},
    {"role": "user", "content": "I joined recently. What should I focus on this quarter?"},
    {"role": "assistant", "content": "coaching"},
    {"role": "user", "content": "how many learning hours do I need this year, and how many have I done?"},
    {"role": "assistant", "content": "policy"},
    {"role": "user", "content": "Can I book flights and hotel in Bahrain for training?"},
    {"role": "assistant", "content": "general"},
]

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
    """Detects if question asks about company rules, approvals, or degree sponsorship in EN or AR."""

    # new implementation
    full_passage = CLASSIFICATION_EXAMPLES + [{"role" : "user", "content" : question}]
    result = few_shot_caller(full_passage)

    res_clean = result.strip().lower()
    if "general" in res_clean:
        return 3
    elif "policy" in res_clean:
        return 1
    else: # coaching
        return 2
