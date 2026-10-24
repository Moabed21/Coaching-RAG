# Re-exports data preparation and LLM invocation for seamless external usage.

from .input_prep import (
    enrich_skill_with_taxonomy,
    future_skills_gaps,
    get_exact_filename,
    current_skills_gaps,
    get_skill_gaps,
    prepare_llm_input,
)
from .llm_caller import call_llm

def llm_processing_pipeline(employee_info: dict, question: str, rec_courses_and_overdue: dict):
    # 1. Prepare structured context payload
    passage = prepare_llm_input(employee_info, question, rec_courses_and_overdue)

    # 2. Format messages for the LLM
    system_prompt = """You are an expert Learning Coach Agent for Al Dana Group.
    Follow these rules strictly:
    1. If the question asks for course recommendations: Recommend ONLY the courses provided in 'recommended_courses' (typically 2 to 5 courses; NEVER invent or recommend any course outside this list). List overdue mandatory courses first, then role gaps, then career growth.
    2. For each course, provide a 1-line 'why' citing the exact source file (e.g. [lms/course_pages/LD-118.md]).
    3. If a course costs 3,000 QAR or more, explicitly note: 'Requires line manager and HR approval'.
    4. Conclude course recommendations with 2 to 3 coaching questions and 1 concrete next-best action.
    5. If the question is about policies, rules, approvals, or budgets: Answer accurately using the provided 'policy_context' and cite [policy/learning_and_development_policy.pdf].
    6. If the user asks something not covered in the documents (such as sponsoring an MBA or degree programme), explicitly say: "I couldn't find that in the documents. Please contact the HR Learning & Development desk at learndesk@aldana-group.example." Do not recommend any courses or coaching questions.
    7. Answer in the same language as the question (Arabic or English)."""

    user_prompt = f"Employee Question: {question}\nContext Information:\n{passage}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    # 3. Ready to invoke call_llm
    return call_llm(messages)
