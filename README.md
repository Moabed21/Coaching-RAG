# Learning Coach RAG Agent — Al Dana Group
**Agent Bank ID 33 | Enterprise Career & Training Recommendation System**

---

## 📌 Project Overview
An enterprise-grade, end-to-end Retrieval-Augmented Generation (RAG) coaching agent for Al Dana Group employees. The system analyzes employee career goals, current role skill gaps, and mandatory compliance requirements to recommend 3 to 5 training courses, grounded in company policy, grade-band budgets, and prerequisites, powered by local **Ollama 7B (`qwen2.5:7b`)**.

---

## 🏗️ Architecture & Pipeline Flow

```
                      ┌────────────────────────────────────────┐
                      │ User Input: asker_id + question        │
                      └───────────────────┬────────────────────┘
                                          │
                                          ▼
                      ┌────────────────────────────────────────┐
                      │ 1. Privacy & Target Detection          │
                      │    (Self or Direct Report only - Sec 5)│
                      └───────┬────────────────────────┬───────┘
           Unauthorized Record│                        │Authorized
                              ▼                        ▼
                   ┌────────────────────┐   ┌───────────────────────────────┐
                   │ Polite Decline     │   │ 2. Intent Routing             │
                   │ (DEV-15)           │   │    (Policy QA vs Coaching)    │
                   └────────────────────┘   └───────┬───────────────┬───────┘
                                                    │               │
                                   Is Policy Question               │ Course Coaching
                                                    ▼               ▼
                        ┌───────────────────────────────┐ ┌───────────────────────────────┐
                        │ Dense Policy Retrieval        │ │ Overdue Mandatory Calculation │
                        │ (Chroma policies_collection)  │ │ (Hire + 60d or Expiration)    │
                        └───────────────┬───────────────┘ └───────────────┬───────────────┘
                                        │                                 │
                                        │                                 ▼
                                        │                 ┌───────────────────────────────┐
                                        │                 │ Eligibility & Pre-Exclusions  │
                                        │                 │ (Retired, Prereqs, Grade, etc)│
                                        │                 └───────────────┬───────────────┘
                                        │                                 │
                                        │                                 ▼
                                        │                 ┌───────────────────────────────┐
                                        │                 │ Hybrid Retrieval              │
                                        │                 │ (BM25 30% + Chroma Dense 70%) │
                                        │                 └───────────────┬───────────────┘
                                        │                                 │
                                        │                                 ▼
                                        │                 ┌───────────────────────────────┐
                                        │                 │ Cumulative Budget Filter      │
                                        │                 │ (Total Optional <= Budget)    │
                                        │                 └───────────────┬───────────────┘
                                        │                                 │
                                        └───────────────┬─────────────────┘
                                                        │
                                                        ▼
                                        ┌───────────────────────────────┐
                                        │ 3. Context & Prompt Assembly  │
                                        │    (Titles, Citations, Gaps)  │
                                        └───────────────┬───────────────┘
                                                        │
                                                        ▼
                                        ┌───────────────────────────────┐
                                        │ 4. Local Ollama 7B Inference  │
                                        │    (qwen2.5:7b @ temp=0)      │
                                        └───────────────┬───────────────┘
                                                        │
                                                        ▼
                                        ┌───────────────────────────────┐
                                        │ 5. Structured Grounded Output │
                                        │    • Mandatory First          │
                                        │    • 1-line Why with Citation │
                                        │    • 2-3 Coaching Questions   │
                                        │    • 1 Next-Best Action       │
                                        └───────────────────────────────┘
```

---

## ⚙️ Core System Layers

### 1. Request Intake & Privacy Layer ([`main.py`](main.py))
- **Target Detection**: Parses questions to determine if the asker is inquiring about themselves or a colleague/direct report (`extract_target_employee`).
- **Section 5 Compliance**: Strictly validates that askers only access their own records or those of direct reports (`check_privacy_access`). Unauthorized inquiries (e.g. `DEV-15`) are politely declined.
- **Audit Logging**: Appends a clean single-line log to `log.log` for every request:
  `REQUEST | Asker: E1055 | Target: E1056 | Status: DECLINED`

### 2. Business Rules & Eligibility Engine ([`filters/`](filters/))
- **Pre-Retrieval Exclusions** ([`before_retrieval.py`](filters/before_retrieval.py)):
  - Excludes courses marked **Retired** in the catalog.
  - Excludes completed courses that are still valid.
  - Excludes courses exceeding employee grade limits (`min_grade > grade`).
  - Excludes courses where prerequisites have not been completed.
  - Excludes courses costing more than remaining individual budget.
- **Mandatory Renewals First**:
  - New joiners must complete mandatory training within 60 days of hire date.
  - Existing staff must renew before `last_completed + renewal_months`.
  - Overdue courses (`LD-106`, `LD-107`, `LD-108`, `LD-117`, `LD-118`) are prioritized and placed first.
- **Cumulative Budget Capping** ([`after_retrieval.py`](filters/after_retrieval.py)):
  - Unlike individual course filtering, `filter_by_cumulative_budget` accumulates course fees and caps the total sum of recommended optional courses so they strictly never exceed the employee's remaining 2026 grade-band budget.
- **Fee Approval Rule**: Courses $\ge \text{QAR } 3{,}000$ explicitly notify the employee that line manager and HR approval is required (Section 4).

### 3. Hybrid Retrieval & Embeddings Layer ([`embeddings.py`](embeddings.py))
- **Course Collection**: Markdown course pages parsed with frontmatter and indexed using `nomic-embed-text` in Chroma.
- **Policy Collection**: Policy PDF (`learning_and_development_policy.pdf`) chunked and indexed into a dedicated collection.
- **Ensemble Retriever**: Uses LangChain's `EnsembleRetriever` combining:
  - **BM25 Sparse Search** (weight: `0.3`) for exact keyword matches (e.g., course codes, job titles).
  - **Dense Chroma Search** (weight: `0.7`) for semantic matching of career aspirations.
- **Intent-Scoped Policy Retrieval**: Automatically routes policy questions (e.g., approvals, budget year rules, degree/MBA sponsorship) to `retrieve_policy` without polluting coaching prompts.

### 4. Agent & LLM Generation Layer ([`agent/`](agent/))
- **Local LLM**: Powered by local **Ollama 7B (`qwen2.5:7b`)** running on `http://localhost:11434/v1` via OpenAI-compatible API at `temperature=0` for fast, deterministic, token-free inference.
- **Strict Grounding & Citation**: Every recommendation cites its source markdown file (e.g. `[lms/course_pages/LD-118.md]`).
- **Out-of-Scope Fallback**: For questions not covered in policy documents (e.g., `DEV-14` MBA sponsorship), the agent outputs:
  *"I couldn't find that in the documents"* and points to `learndesk@aldana-group.example`.
- **Multilingual**: Detects language preference and natively responds in Arabic or English (`DEV-10`).

---

## 📊 Benchmark Evaluation Scorecard

Evaluated against all 15 benchmark test cases in [`data/eval/dev_set.jsonl`](data/eval/dev_set.jsonl) using [`evaluation.py`](evaluation.py):

| Test Case | Category | Key Challenge | Result | Status |
|---|---|---|:---:|:---:|
| **DEV-01** | Coaching | Senior Accountant targeting Finance Manager; overdue LD-118 | 0 violations, budget compliant | **PASS** |
| **DEV-02** | Coaching | Maintenance Engineer targeting Senior Engineer; RCM prereqs | 0 violations, budget compliant | **PASS** |
| **DEV-03** | Coaching | Site Engineer; LD-104 costs QAR 3,800 approval note; overdue LD-108 | Overdue first, approval noted | **PASS** |
| **DEV-04** | Coaching | HSE Officer targeting Supervisor; grade restrictions on LD-122/123 | Excluded G5/G7, budget compliant | **PASS** |
| **DEV-05** | Coaching | New joiner in HSE; 2 overdue mandatory courses (LD-107, LD-108) | Both mandatory listed first | **PASS** |
| **DEV-06** | Coaching | Maintenance Engineer with tight QAR 2,400 remaining budget | Capped to 2 courses (QAR 2,200) | **PASS** |
| **DEV-07** | Coaching | IT Support targeting Systems Analyst opening | 0 violations, budget compliant | **PASS** |
| **DEV-08** | Coaching | Procurement Specialist; overdue ethics renewal LD-117 | LD-117 listed first | **PASS** |
| **DEV-09** | Coaching | Operations Manager targeting Senior Ops Manager; overdue LD-108 | Overdue first, budget compliant | **PASS** |
| **DEV-10** | Coaching | Operations Manager (Arabic preference); Arabic coaching question | Arabic output, budget compliant | **PASS** |
| **DEV-11** | Coaching | HSE Officer targeting internal posting; completed LD-103 | LD-103 excluded, 0 violations | **PASS** |
| **DEV-12** | Coaching | Line manager asking about direct report (Vikram Varma); overdue LD-106 | LD-106 first, direct report authorized | **PASS** |
| **DEV-13** | Policy QA | QAR 3,800 RCM course approval rule and budget year charging | Section 4 & 3 policy cited | **PASS** |
| **DEV-14** | Not In Docs | Employee asking for MBA sponsorship | Out-of-scope fallback + learndesk | **PASS** |
| **DEV-15** | Decline | Employee asking for peer's private development review | Polite privacy decline (Section 5) | **PASS** |

**Final Score: 15 / 15 Passed (100.0%)**

---

## 🚀 How to Run

### 1. Prerequisites
- Python 3.10+
- Ollama running locally with `qwen2.5:7b` and `nomic-embed-text`:
  ```bash
  ollama pull qwen2.5:7b
  ollama pull nomic-embed-text
  ```

### 2. Run Main Program
```bash
python3 main.py
```

### 3. Run Automated Evaluation Suite
Run all 15 test cases:
```bash
python3 evaluation.py
```
Or run a specific test case:
```bash
python3 evaluation.py DEV-04
```

---

## 🛠️ Engineering Challenges & Problem Resolution Log

During the development and testing of this agentic RAG system, several subtle distributed and architectural challenges were identified, diagnosed, and resolved:

1. **Ollama Base URL Misconfiguration:**
   - *Problem:* `.env` contained `OLLAMA_BASE_URL=""`, causing `os.getenv("OLLAMA_BASE_URL", default)` to return an empty string rather than falling back, throwing an OpenAI connection error.
   - *Solution:* Refactored to `os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434/v1"`.

2. **LLM Course Topic Hallucination (Information Deficit):**
   - *Problem:* The LLM hallucinated that `LD-101` was a "leadership" course because the prompt provided only raw course IDs without course titles, descriptions, or taxonomy tags.
   - *Solution:* Diagnosed as an **information deficit** rather than a model size flaw. Injected rich course metadata, skills, and titles into the context passage.

3. **Context Bleed / Prompt Pollution from Policy Chunks:**
   - *Problem:* Unconditionally retrieving policy chunks injected mentions of unrelated courses like `LD-123 Operational Leadership (G7)` and `LD-118 Cybersecurity` into coaching prompts, causing the LLM to recommend forbidden or unqualified courses (`DEV-02`, `DEV-04`, `DEV-07`, `DEV-09`).
   - *Solution:* Built `is_policy_question()` routing to strictly separate coaching pipelines from policy inquiries (`policy_snippets = []` during coaching).

4. **Cumulative Learning Budget Violations:**
   - *Problem:* The retriever suggested individual courses that each met budget individually, but their combined sum exceeded the employee's remaining 2026 grade-band budget (`DEV-01`, `DEV-02`, `DEV-03`, `DEV-06`, `DEV-07`, `DEV-12`).
   - *Solution:* Implemented `filter_by_cumulative_budget()` in `filters/after_retrieval.py` to accumulate course costs and greedily cap optional recommendations within remaining funds.

5. **Low-Budget Over-Recommendation & Padding Hallucination:**
   - *Problem:* For low-budget employees (e.g. `DEV-06` with QAR 2,400 remaining), the LLM hallucinated an extra course (`LD-118`) because Rule 1 rigidly commanded "Recommend 3 to 5 courses".
   - *Solution:* Updated Rule 1 in `agent/__init__.py`: "Recommend ONLY the courses provided in 'recommended_courses' (typically 2 to 5 courses; NEVER invent or recommend any course outside this list)."

6. **Cross-Lingual (Arabic/English) BM25 Zero-Score Failure:**
   - *Problem:* BM25 sparse matching (`sparse = 1.0`) against the English policy PDF yielded a score of `0.00` for Arabic queries due to zero token overlap.
   - *Solution:* Preserved dense vector embeddings (`nomic-embed-text`) for cross-lingual semantic search and added bilingual keywords to `is_policy_question()`.

7. **Course List Leakage on Policy & Out-of-Scope Queries (`DEV-14`):**
   - *Problem:* On MBA sponsorship queries (`DEV-14`), the pipeline still appended `ego["overdue"]` into `recommended_courses`, prompting the LLM to recommend courses alongside the fallback statement.
   - *Solution:* Set `final_picks = []` and `overdue_picks = []` when `is_policy_question` is `True`, explicitly instructed the model in Rule 6, and broadened evaluation to handle straight/curly apostrophes.

8. **Role Profile Markdown Table Parsing:**
   - *Problem:* Regex parsing of markdown role profiles failed to extract skill names along with IDs and target levels.
   - *Solution:* Upgraded regex in `agent/input_prep.py` to `\|\s*(SK-\d+)\s*\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|`, extracting structured `{name, target_level}` dictionaries.

9. **UnboundLocalError in Branching Logic:**
   - *Problem:* In `filters/__init__.py`, `candidates` was unassigned inside the policy branch, throwing an `UnboundLocalError`.
   - *Solution:* Properly initialized `candidates = []`, `final_picks = []`, and `overdue_picks = []` across all execution branches.

10. **Privacy Access Control (Section 5 Compliance):**
    - *Problem:* Employees inquiring about peers rather than direct reports (e.g., `DEV-15`).
    - *Solution:* Integrated `extract_target_employee` and `check_privacy_access` in `main.py` to verify direct reporting lines in `hris/employees.csv` and decline unauthorized requests before running retrieval.
