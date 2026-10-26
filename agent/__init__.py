# Re-exports data preparation and LLM invocation for seamless external usage.

from .input_prep import (
    enrich_skill_with_taxonomy,
    future_skills_gaps,
    get_exact_filename,
    current_skills_gaps,
    get_skill_gaps,
    prepare_llm_input,
)
from .llm_caller import call_llm, few_shot_caller

def llm_processing_pipeline(employee_info: dict, question: str, rec_courses_and_overdue: dict):
    # 1. Prepare structured context payload
    passage = prepare_llm_input(employee_info, question, rec_courses_and_overdue)

    # 2. Format messages for the LLM
    system_prompt = """You are an expert Learning Coach Agent for Al Dana Group.
    The system has already selected the courses, costs, approval notes, and sources below. Do NOT change, add, or remove any course, cost, title, or approval note.
    Follow these rules strictly:
    1. Reproduce every course line from 'course_recommendation_lines' exactly as written (title, cost, source, approval note). Do NOT invent or recommend any course outside this list.
    2. After each course line, add exactly one sentence explaining WHY this course is relevant to the employee's role, skill gaps, or career goals.
    3. Conclude with 2 to 3 coaching questions and 1 concrete next-best action.
    4. If the question is about policies, rules, approvals, budgets, or learning hours: Answer accurately using the provided 'policy_context' and 'learning_hours' data, and cite [policy/learning_and_development_policy.pdf].
    5. Answer in the same language as the question (Arabic or English)."""

    user_prompt = f"Employee Question: {question}\nContext Information:\n{passage}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    # 3. Ready to invoke call_llm
    return call_llm(messages)
