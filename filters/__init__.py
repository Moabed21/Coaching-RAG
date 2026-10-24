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
    filter_recommended_courses,
    filter_by_cumulative_budget,
    is_policy_question
)
from embeddings import embedder_retriever, retrieve_policy
from helpers.structured_data_helpers import get_employee_goals_and_overdue
from agent import llm_processing_pipeline

# AI assisted
def process_request(id: str, question: str):

    # Retrieve policy chunks ONLY if this is a policy question
    if is_policy_question(question):
        policy_docs = retrieve_policy(question, top_k=2)
        policy_snippets = [doc.page_content for doc in policy_docs]
    else:
        policy_snippets = []

    # 1. Overdue mandatory and career context
    ctx = get_employee_goals_and_overdue(id)
    excluded = get_all_excluded_courses(id)
    
    # 2. Enrich search query and retrieve courses
    enriched_query = f"{question} {ctx['career_interest']} {ctx['posting_title']}".strip()
    results = embedder_retriever(enriched_query, top_k=10)
    candidates = [doc.metadata["course_id"] for doc in results if doc.metadata.get("course_id")]
    
    
    # 3. Post-filter exclusions
    valid_courses = filter_recommended_courses(candidates, excluded)
    
    # Deduplicate candidates and exclude already picked overdue courses
    optional_candidates = [c for c in dict.fromkeys(valid_courses) if c not in ctx["overdue"]]
    
    # 4. Cap cumulative optional courses within remaining budget
    max_optional = 5 - len(ctx["overdue"])
    budget_approved_optional = filter_by_cumulative_budget(id, optional_candidates, max_courses=max_optional)
    
    # Overdue mandatory first, then budget-approved optional courses
    final_picks = ctx["overdue"] + budget_approved_optional

    return (llm_processing_pipeline(
        get_employee_by_id(id),
        question,
            {
                "overdue_mandatory": ctx["overdue"],
                "recommended_courses": final_picks,
                "policy_context": policy_snippets
            }))
    
