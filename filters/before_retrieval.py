import pandas as pd
from helpers.structured_data_helpers import (
    get_employee_by_id,
    get_employee_completions_by_id,
    db
)

GRADE_BUDGETS = {
    1: 2500, 2: 2500, 3: 2500,
    4: 6000, 5: 6000, 6: 6000,
    7: 12000, 8: 12000,
    9: 20000, 10: 20000
}

def exclude_retired_courses() -> list[str]:
    """Excludes courses that are marked Retired in the catalog."""
    catalog = db["catalog"]
    return catalog[catalog["status"].str.lower() == "retired"]["course_id"].tolist()

def exclude_not_expired_courses(employee_id: str) -> list[str]:
    """Excludes courses the employee has already completed and are still valid."""
    completion_data = get_employee_completions_by_id(employee_id)
    if isinstance(completion_data, dict) or completion_data.empty:
        return []

    now = pd.Timestamp("2026-10-16")
    renewal_months_map = dict(zip(db["mandatory"]["course_id"], db["mandatory"]["renewal_months"]))
    valid_courses = []

    for _, row in completion_data.iterrows():
        course_id = row['course_id']
        completed_on = pd.to_datetime(row['completed_on'])

        if course_id in renewal_months_map:
            renewal_months = renewal_months_map[course_id]
            expiration_date = completed_on + pd.DateOffset(months=renewal_months)
            if expiration_date >= now:
                valid_courses.append(course_id)
        else:
            valid_courses.append(course_id)
            
    return valid_courses

def exclude_below_min_grade(employee_id: str) -> list[str]:
    """Excludes courses where minimum grade is higher than employee grade."""
    employee = get_employee_by_id(employee_id)
    emp_grade = int(employee["grade"])
    
    catalog = db["catalog"]
    below_grade = []
    for _, row in catalog.iterrows():
        min_grade = int(row["min_grade"])
        if emp_grade < min_grade:
            below_grade.append(row["course_id"])
            
    return below_grade

def get_remaining_budget(employee_id: str) -> int:
    """Calculates remaining budget for the calendar year 2026."""
    emp = get_employee_by_id(employee_id)
    total_budget = GRADE_BUDGETS[int(emp["grade"])]
    
    completions = get_employee_completions_by_id(employee_id)
    if isinstance(completions, dict) or completions.empty:
        return total_budget
        
    spent = 0
    mandatory_ids = set(db["mandatory"]["course_id"])
    catalog_cost = dict(zip(db["catalog"]["course_id"], db["catalog"]["cost_qar"]))
    
    for _, row in completions.iterrows():
        cid = row["course_id"]
        comp_date = str(row["completed_on"])
        if comp_date.startswith("2026") and cid not in mandatory_ids:
            spent += catalog_cost.get(cid, 0)
            
    return total_budget - spent

def exclude_over_budget(employee_id: str) -> list[str]:
    """Excludes courses whose fee exceeds the employee's remaining 2026 budget."""
    remaining = get_remaining_budget(employee_id)
    catalog = db["catalog"]
    return catalog[catalog["cost_qar"] > remaining]["course_id"].tolist()

def exclude_prerequisite_not_met_courses(employee_id: str) -> list[str]:
    """Excludes courses where prerequisite courses have not been completed."""
    already_taken = exclude_not_expired_courses(employee_id)
    all_courses = db.get("catalog", {})
    not_met = []
    for _, row in all_courses.iterrows():
        prereq = row["prerequisites"]
        if pd.notna(prereq) and prereq != "": 
            if prereq not in already_taken:
                not_met.append(row["course_id"])
    return not_met

def get_all_excluded_courses(employee_id: str) -> set[str]:
    """Combines all 5 exclusion filters into a single set of forbidden course IDs."""
    excluded = set()
    excluded.update(exclude_retired_courses())
    excluded.update(exclude_not_expired_courses(employee_id))
    excluded.update(exclude_below_min_grade(employee_id))
    excluded.update(exclude_over_budget(employee_id))
    excluded.update(exclude_prerequisite_not_met_courses(employee_id))
    return excluded

# if __name__ == "__main__":
#     test_id = "E1061"
#     print(f"Testing before_retrieval filters for {test_id}:")
#     print("Excluded courses count:", len(get_all_excluded_courses(test_id)))
#     print("Excluded courses list:", sorted(list(get_all_excluded_courses(test_id))))

