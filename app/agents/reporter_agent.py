import json
from openai import OpenAI
from typing import Dict, Any
from ..config import OPENAI_API_KEY, OPENAI_MODEL

client = OpenAI(api_key=OPENAI_API_KEY)

REPORTER_SYSTEM = """You are the Reporter Agent.
- Build the final JSON object (FinalReport) from provided analysis.
- No prose. Output MUST be a pure JSON object with keys:
  price, monthly_rent, monthly_costs,
  roi {roi_percent, annual_net_eur, guard},
  loan or null,
  warnings [],
  recommendation ("BUY"|"HOLD"|"AVOID"),
  critic_status ("approved"|"rejected"),
  critic_reason (string|null)
"""

def report(analysis_bundle: Dict[str, Any], min_yield: float) -> str:
    # We pass min_yield explicitly; the model should reflect it in warnings if relevant
    messages = [
        {"role":"system","content":REPORTER_SYSTEM},
        {"role":"system","content":f"[PREFS]\nmin_yield_percent={min_yield}"},
        {"role":"user","content":json.dumps(analysis_bundle)}
    ]
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        temperature=0.0,
        response_format={"type":"json_object"}
    )
    return resp.choices[0].message.content
