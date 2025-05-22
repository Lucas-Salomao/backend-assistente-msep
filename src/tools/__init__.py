from .chatmsep_tool import chatmsep
from .pdf_extraction_tool import extract_full_plan_details
from .teaching_plan_tool import generate_teaching_plan
# from .web_search import tool as web_search_tool

tools = [
    chatmsep,
    extract_full_plan_details,
    generate_teaching_plan,
    # web_search_tool,
]