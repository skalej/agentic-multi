from openai import OpenAI
from typing import List, Dict, Any
from ..config import OPENAI_API_KEY, OPENAI_MODEL

client = OpenAI(api_key=OPENAI_API_KEY)

PLANNER_SYSTEM = """You are the Planner Agent.
- Read the user's query and [PREFS], then output a compact plan as JSON:
  {"steps":[ "compute_roi", "maybe_compute_loan", "report_json" ], "needs":{"price":true,"monthly_rent":true,"monthly_costs":true,"loan":false}}
- If loan words appear (loan, mortgage, principal, rate, years), set needs.loan=true and include "compute_loan" in steps.
- No prose. JSON only.
"""

def plan(query: str, prefs_text: str, rag_text: str) -> Dict[str, Any]:
    messages = [
        {"role":"system","content":PLANNER_SYSTEM},
        {"role":"system","content":f"[PREFS]\n{prefs_text}"},
        {"role":"system","content":f"[RAG]\n{rag_text}"},
        {"role":"user","content":query}
    ]
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        temperature=0.0,
        response_format={"type":"json_object"}
    )
    return resp.choices[0].message
