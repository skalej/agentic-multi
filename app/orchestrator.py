import json
from typing import Dict, Any
from openai import OpenAI
from .config import OPENAI_API_KEY, OPENAI_MODEL, MIN_YIELD_PERCENT
from .memory import MEM, get_latest_min_yield, note_from_report
from .agents.planner_agent import plan as planner_plan
from .agents.analyst_agent import analyze as analyst_analyze
from .agents.critic_agent import review as critic_review
from .agents.reporter_agent import report as reporter_report
from .tools import recommendation_from_roi

client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PREFS_LINE = "Use [PREFS] as the single source of truth for user preferences."

def run_analysis(user_query: str) -> str:
    # 1) gather memory and effective prefs
    rag_hits = "\n".join(MEM.search(user_query, k=3)) or "no memory hits"
    min_yield = get_latest_min_yield(MIN_YIELD_PERCENT)
    prefs_text = f"min_yield_percent={min_yield}"

    # 2) planner
    plan_msg = planner_plan(user_query, prefs_text, rag_hits)
    plan_content = plan_msg.content
    try:
        plan_obj = json.loads(plan_content)
    except Exception as e:
        # fallback plan
        plan_obj = {"steps":["compute_roi","report_json"],"needs":{"price":True,"monthly_rent":True,"monthly_costs":True,"loan":False}}

    # 3) analyst
    analysis = analyst_analyze(user_query, plan_obj.get("needs", {}))
    if "error" in analysis:
        # minimal reporter fallback as JSON
        return json.dumps({"error":"missing_fields","detail":analysis["error"]}, ensure_ascii=False)

    # 4) derive base recommendation
    roi_pct = analysis["roi"]["roi_percent"]
    reco = recommendation_from_roi(roi_pct, min_yield)

    # 5) build warnings before critic
    warnings = []
    guard = analysis["roi"].get("guard")
    if guard:
        warnings.append(guard)
    if roi_pct < min_yield:
        warnings.append(f"ROI is below the minimum yield of {min_yield}%")

    # 6) critic
    critic_status, critic_reason = critic_review(roi_pct, warnings, min_yield)

    # 7) reporter (LLM → FinalReport JSON)
    bundle = {
        "price": analysis["price"],
        "monthly_rent": analysis["monthly_rent"],
        "monthly_costs": analysis["monthly_costs"],
        "roi": analysis["roi"],
        "loan": analysis.get("loan"),
        "warnings": warnings,
        "recommendation": reco,
        "critic_status": critic_status,
        "critic_reason": critic_reason,
        "context": {
            "plan": plan_obj,
            "prefs": prefs_text,
            "rag_hits": rag_hits
        }
    }
    final_json = reporter_report(bundle, min_yield)

    # 8) save note
    try:
        data = json.loads(final_json)
        MEM.add_if_not_exists(note_from_report(data))
        MEM.save()
    except Exception as e:
        pass

    return final_json
