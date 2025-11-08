from openai import OpenAI
from typing import Dict, Any, List
from ..config import OPENAI_API_KEY, OPENAI_MODEL

client = OpenAI(api_key=OPENAI_API_KEY)

PLANNER_SYSTEM = """You are the Planner Agent.
Your job has TWO modes:

(Mode A) PLAN:
- Read the user's query and [PREFS] and [RAG], then output a compact plan as JSON:
  {
    "steps":[ "compute_roi", "maybe_compute_loan", "critic_review", "report_json" ],
    "needs": { "price": true, "monthly_rent": true, "monthly_costs": true, "loan": false }
  }
Rules:
- Always include "compute_roi" and "report_json".
- If the user mentions loan/mortgage (principal, rate, years), set needs.loan=true and include "compute_loan".
- If the user asks about whether it's a good deal, worth it, recommendation, compare to threshold/min_yield, or uses words like "good", "worth", "should I buy", "recommend", add "critic_review".
- Output ONLY JSON. No prose.

(Mode B) RECOVERY_QUESTION:
- When given a list of missing fields, produce ONE short natural-language question to ask the user for exactly those fields.
- Your output MUST be JSON:
  { "ask": "..." }
- No prose beyond JSON.

Be strict about JSON. Never output explanations or any text outside JSON.
"""

def _llm_json(messages) -> Dict[str, Any]:
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        temperature=0,
        response_format={"type":"json_object"}
    )
    return resp.choices[0].message

def plan(query: str, prefs_text: str, rag_text: str) -> Dict[str, Any]:
    messages = [
        {"role":"system","content":PLANNER_SYSTEM},
        {"role":"system","content":f"[PREFS]\n{prefs_text}"},
        {"role":"system","content":f"[RAG]\n{rag_text}"},
        {"role":"user","content":query}
    ]
    return _llm_json(messages)

def recovery_question(missing_fields: List[str], query: str, prefs_text: str) -> Dict[str, Any]:
    """Ask Planner to generate a single follow-up question for missing data."""
    messages = [
        {"role":"system","content":PLANNER_SYSTEM},
        {"role":"system","content":f"[PREFS]\n{prefs_text}"},
        {"role":"user","content":f"MODE=RECOVERY_QUESTION\nmissing={missing_fields}\noriginal_query={query}"}
    ]
    return _llm_json(messages)
