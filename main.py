import logging
import re
import pandas as pd
from helpers import get_employee_by_id, db
from filters import process_request

logger = logging.getLogger(__name__)
logging.basicConfig(filename='log.log', encoding='utf-8', level=logging.INFO)


# to filter mandatory and optional courses, after filtering i must validate the taken courses to check if any retirements or 
# course expiry or any other action based on the question, after all that i must implement llm api to answer the question
# along with the top 5 relevant courses from embedding model.
# the final answer must be in the same language as the question
# if cost of a course >= 3000 riyals or equal , then i must ask for manager approval

def extract_target_employee(asker_id: str, question: str) -> str:
    """Detects if another employee's ID or name is mentioned in the prompt."""
    employees = db["employees"]
    q_lower = question.lower()
    
    # 1. Check if another employee's ID is explicitly mentioned (e.g. E1056)
    found_ids = re.findall(r"\bE\d{3,5}\b", question, re.IGNORECASE)
    for eid in found_ids:
        eid_upper = eid.upper()
        if eid_upper in employees["employee_id"].values and eid_upper != asker_id:
            return eid_upper

    # 2. Check if another employee's name is mentioned
    for _, row in employees.iterrows():
        name_en = str(row["full_name_en"]).strip().lower() if pd.notna(row["full_name_en"]) else ""
        name_ar = str(row["full_name_ar"]).strip() if pd.notna(row["full_name_ar"]) else ""
        
        # If their full name is in the question, they are the target
        if (name_en and len(name_en) > 3 and name_en in q_lower) or (name_ar and len(name_ar) > 3 and name_ar in question):
            return row["employee_id"]
            
    # Default: the asker is asking about themselves
    return asker_id

def check_privacy_access(asker_id: str, target_id: str) -> bool:
    """Verifies if asker is allowed to access target employee's records."""
    if asker_id == target_id:
        return True
    target_emp = get_employee_by_id(target_id)
    # Check if asker is the line manager
    return target_emp.get("manager_id") == asker_id

# if i'm taking an employee id , i must know the role of the employee to apply the correct filters 
def get_employee_id_and_question(asker_id: str, question: str):
    if not verify_employee_id(asker_id):
        return "Employee not found."

    # 1. Who is the question about?
    target_id = extract_target_employee(asker_id, question)

    # 2. Privacy check (Section 5 of Policy)
    if not check_privacy_access(asker_id, target_id):
        logger.info(f"REQUEST | Asker: {asker_id} | Target: {target_id} | Status: DECLINED")
        return (
            "I cannot share another employee's records. You may only view your own "
            "records or those of your direct reports. Would you like help with your own learning plan instead?"
        )

    # 3. Authorized -> process request for target_id
    logger.info(f"REQUEST | Asker: {asker_id} | Target: {target_id} | Status: SUCCESS")
    return process_request(target_id, question)


def verify_employee_id(id: str) -> bool:
    emp = get_employee_by_id(id)
    return bool(len(emp) > 0)

if __name__ == "__main__":
    e_id = 'E1056'
    question = 'I want to move into a supervisor role. What training should I do?'
    answer = get_employee_id_and_question(e_id, question)
    print(answer)
