# Responsible for gathering employee context, identifying current and future 
# skill gaps, and assembling the structured payload for the LLM.

from helpers import (
    get_employee_skills_by_id,
    db
)
from chunking import get_all_files_by_ex
import re
import frontmatter

def enrich_skill_with_taxonomy(skill_id: str) -> dict:
    """Enriches a skill ID with its English and Arabic names from roles/skills_taxonomy.csv."""
    taxonomy = db["taxonomy"]
    match = taxonomy[taxonomy["skill_id"] == skill_id]
    if not match.empty:
        row = match.iloc[0]
        return {"skill_id": skill_id, "name_en": row["name_en"], "name_ar": row["name_ar"]}
    return {"skill_id": skill_id, "name_en": skill_id, "name_ar": skill_id}

def future_skills_gaps(employee_info: dict) -> dict:
    # First check interest of emp in ATS postings, if none check development reviews
    employee_id = employee_info["employee_id"]
    interest = dict(zip(db["interest"]["employee_id"], db["interest"]["posting_id"]))
    post = None
    for k, v in interest.items():
        if k == employee_id:
            post = v
            break

    emp_skills = get_employee_skills_by_id(employee_id)
    ratings_map = dict(zip(emp_skills["skill_id"], emp_skills["manager_rating"]))
    future_gaps = {}

    if post:
        # Branch A: Look up required_skills and expected_level in ats/internal_postings.csv
        p_match = db["postings"][db["postings"]["posting_id"] == post]
        if not p_match.empty:
            p_row = p_match.iloc[0]
            expected_level = int(p_row["expected_level"])
            req_skills = [s.strip() for s in str(p_row["required_skills"]).split(";") if s.strip()]
            for skill_id in req_skills:
                manager_rating = ratings_map.get(skill_id, 0)
                if manager_rating < expected_level:
                    future_gaps[skill_id] = expected_level - manager_rating
    else:
        # Branch B: Read career_interest and development_areas from hris/development_reviews.csv
        r_match = db["reviews"][db["reviews"]["employee_id"] == employee_id]
        if not r_match.empty:
            r_row = r_match.iloc[0]
            c_int = str(r_row["career_interest"]) if "career_interest" in r_row else ""
            d_area = str(r_row["development_areas"]) if "development_areas" in r_row else ""
            dev_text = (c_int + " " + d_area).lower()
            for _, tax_row in db["taxonomy"].iterrows():
                sk_id = tax_row["skill_id"]
                name_en = str(tax_row["name_en"]).lower()
                synonyms = [s.strip().lower() for s in str(tax_row.get("synonyms", "")).split(";")]
                if name_en in dev_text or any(syn in dev_text for syn in synonyms if syn):
                    manager_rating = ratings_map.get(sk_id, 0)
                    if manager_rating < 3:
                        future_gaps[sk_id] = 3 - manager_rating

    return future_gaps

    # Parses role profile markdown files to extract skill table target levels
def get_exact_filename(role_id: str):
    all_mds = get_all_files_by_ex("data/roles/role_profiles", "md")
    for file in all_mds:
        f = frontmatter.load(file)
        if f.get("role_profile_id") == role_id:
            matches = re.findall(r"\|\s*(SK-\d+)\s*\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|", f.content)
            target_skills = {
                skill_id:{
                    "name":name.strip(),
                    "target_level":int(target)
                } 
                for skill_id, name, target in matches
                }
            break
    return target_skills

def current_skills_gaps(employee_info: dict) -> dict:
    # Extracts current skills and compares against role profile targets
    employee_id = employee_info["employee_id"]
    role_profile_id = employee_info["role_profile_id"]

    current_role_skills = get_exact_filename(role_profile_id)
    emp_skills = get_employee_skills_by_id(employee_id)

    # Map skill_id -> manager_rating
    ratings_map = dict(zip(emp_skills["skill_id"], emp_skills["manager_rating"]))
    current_role_skills_gaps = {}

    for skill_id, skill_info in current_role_skills.items():
        target_level = skill_info["target_level"]
        manager_rating = ratings_map.get(skill_id)
        
        if manager_rating is not None and manager_rating < target_level:
            current_role_skills_gaps[skill_id] = target_level - manager_rating


    return current_role_skills_gaps

def get_skill_gaps(employee_info: dict) -> dict:
    # Combines current role gaps and future goal gaps with taxonomy names
    current_gaps = current_skills_gaps(employee_info)
    future_gaps = future_skills_gaps(employee_info)

    enriched_current = [{**enrich_skill_with_taxonomy(k), "gap": v} for k, v in current_gaps.items()]
    enriched_future = [{**enrich_skill_with_taxonomy(k), "gap": v} for k, v in future_gaps.items()]

    return {
        "current_role_gaps": enriched_current,
        "future_goal_gaps": enriched_future
    }

def prepare_llm_input(employee_info: dict, question: str, rec_courses_and_overdue: dict) -> dict:
    # Assembles the full passage context dictionary for the LLM
    emp_id = employee_info["employee_id"]
    reviews = db["reviews"]

    match = reviews[reviews["employee_id"] == emp_id]
    career_interest = match.iloc[0]["career_interest"] if not match.empty else ""

    # 1. Find posting_id for this employee in internal interest
    interest_match = db["interest"][db["interest"]["employee_id"] == emp_id]

    # 2. Find the posting details from db["postings"] if registered
    if not interest_match.empty:
        post_id = interest_match.iloc[0]["posting_id"]
        job_posting = db["postings"][db["postings"]["posting_id"] == post_id].iloc[0].to_dict()
    else:
        job_posting = None

    passage = {
        "employee_info": employee_info,
        "passage": question,
        "rec_courses_and_overdue": rec_courses_and_overdue,
        "policy_context": rec_courses_and_overdue.get("policy_context", []),
        "career_interest": career_interest,
        "internal_jobs_interest": job_posting,
        "current_skill_gaps": get_skill_gaps(employee_info)
    }
    return passage
