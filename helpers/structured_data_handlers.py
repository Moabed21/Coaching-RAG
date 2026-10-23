# storing a dataframes about csv's
import pandas as pd

# from langchain_experimental.agents.dataframe.tools import (
#     ColumnDescriptionTool, 
#     HeadTool, 
#     TableDescriptionTool, 
#     GetMarkdownSummaryTool, 
#     FilterRowsTool,
#     FilterColumnsTool, 
#     ApplyFunctionTool, 
#     SelectRowsTool, 
#     CalculateStatsTool
# )

def load_all_tables(data_root: str = "data") -> dict:
    tables = {
        "employees":    pd.read_csv(f"{data_root}/hris/employees.csv"),
        "skills":       pd.read_csv(f"{data_root}/hris/skills.csv"),
        "reviews":      pd.read_csv(f"{data_root}/hris/development_reviews.csv"),
        "departments":  pd.read_csv(f"{data_root}/hris/departments.csv"),
        "completions":  pd.read_csv(f"{data_root}/lms/completions.csv"),
        "catalog":      pd.read_csv(f"{data_root}/lms/course_catalog.csv"),
        "mandatory":    pd.read_csv(f"{data_root}/lms/mandatory_matrix.csv"),
        "taxonomy":     pd.read_csv(f"{data_root}/roles/skills_taxonomy.csv"),
        "postings":     pd.read_csv(f"{data_root}/ats/internal_postings.csv"),
        "interest":     pd.read_csv(f"{data_root}/ats/internal_interest.csv"),
    }
    return tables

