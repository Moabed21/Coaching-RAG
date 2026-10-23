try:
    from .structured_data_handlers import load_all_tables
except (ImportError, ValueError):
    from helpers.structured_data_handlers import load_all_tables
import pandas as pd

db  = load_all_tables()

def get_mandatory_courses():
    mandatory_courses = db["mandatory"]
    print(mandatory_courses)
    return mandatory_courses

def get_employee_by_id(id:str) -> dict:
    df = db["employees"]
    match = df[df["employee_id"] == id]
    if match.empty:
        return {}
    return match.iloc[0]

def get_employee_skills_by_id(id: str) ->dict:
    skills = db["skills"]
    match = skills[skills["employee_id"] == id]
    if match.empty:
        return {}
    return match

def get_employee_completions_by_id(id: str) -> dict:
    completions = db["completions"]
    match = completions[completions["employee_id"] == id]
    if match.empty:
        return {}
    return match

def get_optional_courses():
    mandatory_courses = get_mandatory_courses()
    mandatory_ids = mandatory_courses['course_id'].unique()
    catalog = db['catalog']
    # Filter courses whose course_id is NOT in mandatory_ids
    optional_courses = catalog[~catalog['course_id'].isin(mandatory_ids)]
    
    return optional_courses



# this function prevets mutli interesets error
def get_intersets_by_employee(employee_id:str) -> dict:
    interests = db['interest']
    for _, row in interests.iterrows():
        if(row["employee_id"] == employee_id):
            return row
    return None

# AI created
def get_employee_goals_and_overdue(emp_id: str) -> dict:
    emp = get_employee_by_id(emp_id)
    now = pd.Timestamp("2026-10-16")
        
    # 1. Career interest from reviews & postings
    rev = db["reviews"]
    rev_match = rev[rev["employee_id"] == emp_id]
    career_interest = rev_match.iloc[0]["career_interest"] if not rev_match.empty else ""
    
    inter = get_intersets_by_employee(emp_id)
    post_title = ""
    if inter is not None:
        p_row = db["postings"][db["postings"]["posting_id"] == inter["posting_id"]]
        if not p_row.empty:
            post_title = p_row.iloc[0]["title"]
    # 2. Overdue mandatory courses
    emp_comp = db["completions"][db["completions"]["employee_id"] == emp_id]
    overdue = []
    for _, r in db["mandatory"].iterrows():
        cid, scope, applies, months = r["course_id"], r["scope_type"], r["applies_to"], r["renewal_months"]
        applies_flag = (scope == "All") or (scope == "Department" and emp.get("department") == applies) or (scope == "Location" and emp.get("location") == applies)
        if applies_flag:
            cm = emp_comp[emp_comp["course_id"] == cid]
            if cm.empty:
                hire = pd.to_datetime(emp["hire_date"])
                if hire + pd.Timedelta(days=60) < now:
                    overdue.append(cid)
            else:
                last_c = pd.to_datetime(cm["completed_on"].max())
                if last_c + pd.DateOffset(months=months) < now:
                    overdue.append(cid)
                    
    return {"career_interest": career_interest, "posting_title": post_title, "overdue": overdue}