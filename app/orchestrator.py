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
from .logger import log

client = OpenAI(api_key=OPENAI_API_KEY)

def run_analysis(user_query: str) -> str:
    log("USER QUERY", user_query, symbol="💬")

    # 1️⃣ Memory & Prefs
    rag_hits = "\n".join(MEM.search(user_query, k=3)) or "no memory hits"
    min_yield = get_latest_min_yield(MIN_YIELD_PERCENT)
    prefs_text = f"min_yield_percent={min_yield}"
    log("Memory retrieved", rag_hits)
    log("Effective prefs", prefs_text)

    # 2️⃣ Planner
    plan_msg = planner_plan(user_query, prefs_text, rag_hits)
    plan_content = plan_msg.content
    try:
        plan_obj = json.loads(plan_content)
    except Exception:
        plan_obj = {"steps":["compute_roi","report_json"],"needs":{"price":True,"monthly_rent":True,"monthly_costs":True,"loan":False}}
    log("Planner decided", plan_obj, symbol="🧭")

    # 3️⃣ Analyst
    analysis = analyst_analyze(user_query, plan_obj.get("needs", {}))
    log("Analyst results", analysis, symbol="📊")

    if "error" in analysis:
        log("Analyst Error", analysis, symbol="⚠️")
        return json.dumps({
            "error": analysis["error"],
            "detail": analysis.get("missing") or analysis.get("detail") or "unknown",
            "parsed": analysis.get("parsed", {})
        }, ensure_ascii=False)

    # 4️⃣ Recommendation baseline
    roi_pct = analysis["roi"]["roi_percent"]
    reco = recommendation_from_roi(roi_pct, min_yield)
    warnings = []
    guard = analysis["roi"].get("guard")
    if guard:
        warnings.append(guard)
    if roi_pct < min_yield:
        warnings.append(f"ROI is below the minimum yield of {min_yield}%")

    # 5️⃣ Critic
    critic_status, critic_reason = critic_review(roi_pct, warnings, min_yield)
    log("Critic verdict", {"status": critic_status, "reason": critic_reason}, symbol="🧠")

    # 6️⃣ Reporter
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
    log("Reporter Final JSON", final_json, symbol="📝")

    # 7️⃣ Memory save
    try:
        data = json.loads(final_json)
        MEM.add_if_not_exists(note_from_report(data))
        MEM.save()
        log("Memory updated", "✅ note added", symbol="💾")
    except Exception as e:
        log("Memory save error", str(e), symbol="⚠️")

    log("Workflow completed", "✅ All agents done", symbol="🏁")
    return final_json
