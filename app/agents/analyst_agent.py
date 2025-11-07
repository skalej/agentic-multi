import json
from typing import Dict, Any
from openai import OpenAI
from ..config import OPENAI_API_KEY, OPENAI_MODEL
from ..tools import roi_calc, loan_calc

client = OpenAI(api_key=OPENAI_API_KEY)

EXTRACT_SYSTEM = """You are an information-extraction model for real-estate analysis.
Extract the following numeric attributes (if present) from the user's free-text query and return STRICT JSON:
{
  "price": number,
  "monthly_rent": number,
  "monthly_costs": number,
  "principal": number,
  "annual_rate_percent": number,
  "years": number
}
Rules:
- Output ONLY a JSON object; no prose, no explanations.
- Use numbers (not words). Convert “seventy thousand” → 70000.
- If a field is not stated, omit it.
- If a range is given (e.g., 60–70k), pick the midpoint and use a number.
- Accept multiple languages and currency words (€, euro, euros, eur). Ignore currency symbols.
- The keys MUST be exactly as specified above.
"""

def extract_numbers_llm(query: str) -> Dict[str, Any]:
    msgs = [
        {"role": "system", "content": EXTRACT_SYSTEM},
        {"role": "user", "content": query}
    ]
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=msgs,
        temperature=0,
        response_format={"type": "json_object"}
    )
    content = resp.choices[0].message.content or "{}"
    try:
        data = json.loads(content)
        if not isinstance(data, dict):
            return {}
        # keep only allowed keys
        keep = {"price","monthly_rent","monthly_costs","principal","annual_rate_percent","years"}
        return {k: data[k] for k in data.keys() if k in keep and data[k] is not None}
    except Exception:
        return {}

def analyze(query: str, needs: Dict[str, Any]) -> Dict[str, Any]:
    # 🔹 Use LLM-based extraction (no regex)
    nums = extract_numbers_llm(query)

    # ROI requires these 3 keys; enforce defensively
    required_for_roi = ["price", "monthly_rent", "monthly_costs"]
    missing = [k for k in required_for_roi if k not in nums]
    if missing:
        return {
            "error": "missing_fields",
            "missing": missing,
            "parsed": nums
        }

    roi = roi_calc(nums["price"], nums["monthly_rent"], nums["monthly_costs"])
    out = {
        "price": nums["price"],
        "monthly_rent": nums["monthly_rent"],
        "monthly_costs": nums["monthly_costs"],
        "roi": roi
    }

    # Loan only if planner says so AND fields exist
    if needs.get("loan"):
        loan_required = ["principal", "annual_rate_percent", "years"]
        loan_missing = [k for k in loan_required if k not in nums]
        if loan_missing:
            out["loan_error"] = f"loan fields missing: {loan_missing}"
        else:
            out["loan"] = loan_calc(nums["principal"], nums["annual_rate_percent"], nums["years"])

    return out
