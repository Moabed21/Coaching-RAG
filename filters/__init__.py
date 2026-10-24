from helpers.structured_data_helpers import (
    get_employee_by_id,
    get_employee_skills_by_id,
    get_employee_completions_by_id,
    get_mandatory_courses,
    get_optional_courses,
    db
)

from .before_retrieval import (
    GRADE_BUDGETS,
    exclude_retired_courses,
    exclude_not_expired_courses,
    exclude_below_min_grade,
    get_remaining_budget,
    exclude_over_budget,
    exclude_prerequisite_not_met_courses,
    get_all_excluded_courses
)

from .after_retrieval import (
    validate_allowed_grade_courses,
    validate_budget_limit_courses,
    filter_recommended_courses
)
from embeddings import embedder_retriever
from helpers.structured_data_helpers import get_employee_goals_and_overdue
from agent import llm_processing_pipeline

# AI assisted
def process_request(id: str, question: str):
    # 1. Overdue mandatory and career context
    ctx = get_employee_goals_and_overdue(id)
    excluded = get_all_excluded_courses(id)
    
    # 2. Enrich search query and retrieve courses
    enriched_query = f"{question} {ctx['career_interest']} {ctx['posting_title']}".strip()
    results = embedder_retriever(enriched_query, top_k=10)
    candidates = [doc.metadata["course_id"] for doc in results if doc.metadata.get("course_id")]
    
    # 3. Post-filter exclusions and put overdue mandatory first
    valid_courses = filter_recommended_courses(candidates, excluded)
    final_picks = ctx["overdue"] + [c for c in valid_courses if c not in ctx["overdue"]]

    return (llm_processing_pipeline(
        get_employee_by_id(id),
        question,
            {
                "overdue_mandatory": ctx["overdue"],
                "recommended_courses": final_picks[:5]
            }))
    
