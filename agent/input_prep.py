# Responsible for gathering employee context, identifying current and future 
# skill gaps, and assembling the structured payload for the LLM.

from helpers import (
    get_employee_skills_by_id,
    db
)
from chunking import get_all_files_by_ex
import re
import pandas as pd
import frontmatter
from helpers import get_completed_hours_2026

def enrich_skill_with_taxonomy(skill_id: str) -> dict:
    """Enriches a skill ID with its English and Arabic names from roles/skills_taxonomy.csv."""
    taxonomy = db["taxonomy"]
    match = taxonomy[taxonomy["skill_id"] == skill_id]
    if not match.empty:
        row = match.iloc[0]
        return {"skill_id": skill_id, "name_en": row["name_en"], "name_ar": row["name_ar"]}
    return {"skill_id": skill_id, "name_en": skill_id, "name_ar": skill_id}

def get_future_gaps_from_postings(employee_id: str, ratings_map: dict) -> dict:
    """Checks interest in internal ATS postings and computes skill gaps against expected_level."""
    # tie the employee_id's to the internal job postings id's
    interest = dict(zip(db["interest"]["employee_id"], db["interest"]["posting_id"]))
    # get posting id from the employee id
    post = interest.get(employee_id)
    # if no posting id is found, return empty dict
    if not post:
        return {}
    # get the posting from the posting id
    p_match = db["postings"][db["postings"]["posting_id"] == post]
    # if no posting is found, return empty dict
    if p_match.empty:
        return {}
    # get the expected level and required skills from the posting
    p_row = p_match.iloc[0]
    expected_level = int(p_row["expected_level"])
    req_skills = [s.strip() for s in str(p_row["required_skills"]).split(";") if s.strip()]

    # compute the skill gaps from the expected level and manager rating
    future_gaps = {}
    for skill_id in req_skills:
        manager_rating = ratings_map.get(skill_id, 0)
        if manager_rating < expected_level:
            future_gaps[skill_id] = expected_level - manager_rating
    return future_gaps


def get_future_gaps_from_reviews(employee_id: str, ratings_map: dict) -> dict:
    """Checks career interest and development areas in HR reviews and computes skill gaps."""
    # get the employee's hr review
    r_match = db["reviews"][db["reviews"]["employee_id"] == employee_id]
    # if no review is found, return empty dict
    if r_match.empty:
        return {}
    # get the career interest and development areas from the review
    r_row = r_match.iloc[0]
    c_int = str(r_row["career_interest"]) if "career_interest" in r_row else ""
    d_area = str(r_row["development_areas"]) if "development_areas" in r_row else ""
    dev_text = (c_int + " " + d_area).lower()

    # compute the skill gaps from the career interest and development areas
    future_gaps = {}
    for _, tax_row in db["taxonomy"].iterrows():
        sk_id = tax_row["skill_id"]
        name_en = str(tax_row["name_en"]).lower()
        synonyms = [s.strip().lower() for s in str(tax_row.get("synonyms", "")).split(";") if s.strip()]

        # Use word boundaries so substrings like 'lan' don't falsely match 'plan'
        matched = bool(re.search(r"\b" + re.escape(name_en) + r"\b", dev_text))
        if not matched and synonyms:
            matched = any(re.search(r"\b" + re.escape(syn) + r"\b", dev_text) for syn in synonyms)

        if matched:
            manager_rating = ratings_map.get(sk_id, 0)
            # Level 3 is the standard corporate proficiency benchmark ("Competent / Working Level").
            if manager_rating < 3:
                future_gaps[sk_id] = 3 - manager_rating
    return future_gaps


def future_skills_gaps(employee_info: dict) -> dict:
    """Returns future skill gaps: first checks ATS postings, then development reviews."""
    employee_id = employee_info["employee_id"]
    emp_skills = get_employee_skills_by_id(employee_id)
    ratings_map = dict(zip(emp_skills["skill_id"], emp_skills["manager_rating"]))

    # 1. First check interest in ATS postings
    posting_gaps = get_future_gaps_from_postings(employee_id, ratings_map)
    if posting_gaps:
        return posting_gaps

    # 2. Otherwise check development reviews
    return get_future_gaps_from_reviews(employee_id, ratings_map)

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

def get_recommended_courses_context(courses: list) -> list[dict]:
    """Enriches a list of course IDs with title, level, cost, target skills and approval flag from the catalog."""
    
    # get courses catalog and skills taxonomy and iterate over the courses
    recommended_courses_context = []
    catalog = db['catalog']
    taxonomy = db['taxonomy']
    for course_id in courses:
        match = catalog[catalog["course_id"] == course_id]
        if not match.empty:
            row = match.iloc[0]
            # Resolve skill IDs to human-readable names
            raw_skills = str(row["skills"]) if pd.notna(row["skills"]) else ""
            skill_ids = [s.strip() for s in raw_skills.split(";") if s.strip()]
            skill_names = []
            # get course id , title , level , cost and target skills 
            for sid in skill_ids:
                tax_match = taxonomy[taxonomy["skill_id"] == sid]
                if not tax_match.empty:
                    skill_names.append(tax_match.iloc[0]["name_en"])
                else:
                    skill_names.append(sid)
            cost = int(row["cost_qar"])
            recommended_courses_context.append({
                "course_id": course_id,
                "title_en": row["title_en"],
                "title_ar": row["title_ar"],
                "level": row["level"],
                "cost_qar": cost,
                "target_skills": skill_names,
                "requires_approval": cost >= 3000,
            })
    return recommended_courses_context


def build_course_lines(overdue_courses: list[dict], recommended_courses: list[dict]) -> str:
    """Builds pre-formatted course recommendation lines from code so the LLM cannot hallucinate facts."""
    # get overdue courses ids
    overdue_ids = {c["course_id"] for c in overdue_courses}
    # combine overdue and recommended courses
    all_courses = [(c, True) for c in overdue_courses] + [
        (c, False) for c in recommended_courses if c["course_id"] not in overdue_ids
    ]
    # if no courses to recommend, return "No courses to recommend."
    if not all_courses:
        return "No courses to recommend."
    # build course lines, which simply are formatted strings of courses information
    # and each course contains its id, title, level, cost, and target skills and its source mardown file
    # so that the LLM cannot hallucinate facts.
    lines = []
    for idx, (c, is_overdue) in enumerate(all_courses, start=1):
        # if course is overdue, tag it as overdue
        tag = " [OVERDUE MANDATORY]" if is_overdue else ""
        # if course requires approval, add a note about it
        approval = "\nRequires line manager and HR approval (cost ≥ QAR 3,000)." if c["requires_approval"] else ""
        # append the course information to the lines list
        lines.append(
            f"{idx}. **{c['course_id']} — {c['title_en']}** (QAR {c['cost_qar']:,}, {c['level']}){tag}\n"
            f"   Target skills: {', '.join(c['target_skills'])}\n"
            f"   Source: [lms/course_pages/{c['course_id']}.md]{approval}"
        )

    return "\n\n".join(lines)

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

    # Enrich course IDs with catalog metadata
    overdue_enriched = get_recommended_courses_context(rec_courses_and_overdue.get("overdue_mandatory", []))
    recommended_enriched = get_recommended_courses_context(rec_courses_and_overdue.get("recommended_courses", []))

    # Build deterministic course recommendation lines from code
    course_lines = build_course_lines(overdue_enriched, recommended_enriched)

    # get the completed hours by the employee in 2026
    hours_done = get_completed_hours_2026(emp_id)

    # get the required hours for the employee in 2026
    required_hours = 40
    passage = {
        "employee_info": employee_info,
        "passage": question,
        "course_recommendation_lines": course_lines,
        "learning_hours": {
            "annual_target_hours": 40,
            "completed_hours_2026": hours_done,
            "remaining_hours_needed_2026": max(0, 40 - hours_done)
        },
        "policy_context": rec_courses_and_overdue.get("policy_context", []),
        "career_interest": career_interest,
        "internal_jobs_interest": job_posting,
        "current_skill_gaps": get_skill_gaps(employee_info)
    }
    return passage
