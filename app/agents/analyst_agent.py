import json, re
from typing import Dict, Any
from ..tools import roi_calc, loan_calc

def parse_numbers_from_query(q: str) -> Dict[str, float]:
    # very lightweight extraction for demo purposes
    # Looks for 'price', 'rent', 'costs', 'principal', 'rate', 'years'
    out = {}
    m = re.search(r"price\s*([0-9]+(?:\.\d+)?)", q, flags=re.I)
    if m: out["price"] = float(m.group(1))
    m = re.search(r"rent\s*([0-9]+(?:\.\d+)?)", q, flags=re.I)
    if m: out["monthly_rent"] = float(m.group(1))
    m = re.search(r"costs?\s*([0-9]+(?:\.\d+)?)", q, flags=re.I)
    if m: out["monthly_costs"] = float(m.group(1))
    m = re.search(r"principal\s*([0-9]+(?:\.\d+)?)", q, flags=re.I)
    if m: out["principal"] = float(m.group(1))
    m = re.search(r"rate\s*([0-9]+(?:\.\d+)?)", q, flags=re.I)
    if m: out["annual_rate_percent"] = float(m.group(1))
    m = re.search(r"years?\s*([0-9]+)", q, flags=re.I)
    if m: out["years"] = int(m.group(1))
    return out

def analyze(query: str, needs: Dict[str, Any]) -> Dict[str, Any]:
    nums = parse_numbers_from_query(query)
    missing = [k for k in ["price","monthly_rent","monthly_costs"] if needs.get(k, True) and k not in nums]
    if missing:
        return {"error": f"Missing required fields: {missing}"}

    roi = roi_calc(nums["price"], nums["monthly_rent"], nums["monthly_costs"])
    out = {
        "price": nums["price"],
        "monthly_rent": nums["monthly_rent"],
        "monthly_costs": nums["monthly_costs"],
        "roi": roi
    }

    if needs.get("loan"):
        if not all(k in nums for k in ["principal","annual_rate_percent","years"]):
            out["loan_error"] = "loan fields missing"
        else:
            out["loan"] = loan_calc(nums["principal"], nums["annual_rate_percent"], nums["years"])

    return out
