import json
from typing import Dict, Any
from openai import OpenAI
from .config import OPENAI_API_KEY, OPENAI_MODEL, MIN_YIELD_PERCENT
from .memory import MEM, get_latest_min_yield, note_from_report
from .agents.planner_agent import plan as planner_plan, recovery_question as planner_recovery_question
from .agents.analyst_agent import analyze as analyst_analyze, extract_numbers_llm
from .agents.critic_agent import review as critic_review
from .agents.reporter_agent import report as reporter_report
from .tools import recommendation_from_roi
from .logger import log
from .session import SESSIONS

client = OpenAI(api_key=OPENAI_API_KEY)

def run_analysis(user_query: str) -> str:
    log("USER QUERY", user_query, symbol="💬")

    # Memory & Prefs
    rag_hits = "\n".join(MEM.search(user_query, k=3)) or "no memory hits"
    min_yield = get_latest_min_yield(MIN_YIELD_PERCENT)
    prefs_text = f"min_yield_percent={min_yield}"
    log("Memory retrieved", rag_hits)
    log("Effective prefs", prefs_text)

    # Planner plan
    plan_msg = planner_plan(user_query, prefs_text, rag_hits)
    try:
        plan_obj = json.loads(plan_msg.content)
    except Exception:
        plan_obj = {"steps":["compute_roi","report_json"],"needs":{"price":True,"monthly_rent":True,"monthly_costs":True,"loan":False}}
    log("Planner decided", plan_obj)

    # Analyst
    analysis = analyst_analyze(user_query, plan_obj.get("needs", {}))
    log("Analyst results", analysis, symbol="📊")

    # create session and ask follow-up
    if analysis.get("error") == "missing_fields":
        missing = analysis.get("missing", [])
        parsed = analysis.get("parsed", {})
        rq_msg = planner_recovery_question(missing, user_query, prefs_text)
        try:
            rq_obj = json.loads(rq_msg.content)
            ask = rq_obj.get("ask") or f"Please provide: {missing}"
        except Exception:
            ask = f"Please provide: {missing}"

        session_payload = {
            "original_query": user_query,
            "prefs_text": prefs_text,
            "plan_obj": plan_obj,
            "partial_parsed": parsed,
            "missing": missing
        }
        sid = SESSIONS.create(session_payload)
        log("Recovery question (session created)", {"session_id": sid, "ask": ask, "missing": missing, "parsed": parsed})

        return json.dumps({
            "need_more_info": True,
            "session_id": sid,
            "ask": ask,
            "missing": missing,
            "parsed": parsed
        }, ensure_ascii=False)

    # Else continue pipeline normally
    return _finalize_pipeline(plan_obj, analysis, prefs_text, rag_hits, min_yield)

def _finalize_pipeline(plan_obj: Dict[str, Any], analysis: Dict[str, Any],
                       prefs_text: str, rag_hits: str, min_yield: float) -> str:
    # Recommendation
    roi_pct = analysis["roi"]["roi_percent"]
    reco = recommendation_from_roi(roi_pct, min_yield)
    warnings = []
    guard = analysis["roi"].get("guard")
    if guard:
        warnings.append(guard)
    if roi_pct < min_yield:
        warnings.append(f"ROI is below the minimum yield of {min_yield}%")

    # Critic maybe
    if "critic_review" in plan_obj.get("steps", []):
        critic_status, critic_reason = critic_review(roi_pct, warnings, min_yield)
        log("Critic verdict", {"status": critic_status, "reason": critic_reason}, symbol="🧠")
    else:
        critic_status, critic_reason = ("approved", None)
        log("Critic skipped", "planner did not include critic_review", symbol="🧠")

    # Reporter
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

    # Memory save
    try:
        data = json.loads(final_json)
        MEM.add_if_not_exists(note_from_report(data))
        MEM.save()
        log("Memory updated", "✅ note added", symbol="💾")
    except Exception as e:
        log("Memory save error", str(e), symbol="⚠️")

    log("Workflow completed", "✅ All agents done", symbol="🏁")
    return final_json

# continue session after user provided missing values
def continue_session(session_id: str, user_reply: str) -> str:
    log("CONTINUE SESSION", {"session_id": session_id, "user_reply": user_reply}, symbol="🔁")

    sess = SESSIONS.get(session_id)
    if not sess:
        return json.dumps({"error":"invalid_session","detail":"Session not found or expired."})

    original_query = sess["original_query"]
    prefs_text = sess["prefs_text"]
    plan_obj = sess["plan_obj"]
    partial_parsed = sess.get("partial_parsed", {})
    missing = sess.get("missing", [])

    # Use LLM extractor on the user's reply
    extracted = extract_numbers_llm(user_reply)
    log("Extracted from reply", extracted, symbol="📥")

    # Merge
    merged = dict(partial_parsed)
    merged.update({k:v for k,v in extracted.items() if v is not None})
    log("Merged values", merged, symbol="🧩")

    # Check still missing
    required_for_roi = ["price","monthly_rent","monthly_costs"]
    still_missing = [k for k in required_for_roi if k not in merged]
    if still_missing:
        # ask again (same session)
        rq_msg = planner_recovery_question(still_missing, original_query, prefs_text)
        try:
            rq_obj = json.loads(rq_msg.content)
            ask = rq_obj.get("ask") or f"Please provide: {still_missing}"
        except Exception:
            ask = f"Please provide: {still_missing}"

        SESSIONS.update(session_id, {"partial_parsed": merged, "missing": still_missing})
        log("Recovery question (again)", {"session_id": session_id, "ask": ask, "missing": still_missing}, symbol="❓")

        return json.dumps({
            "need_more_info": True,
            "session_id": session_id,
            "ask": ask,
            "missing": still_missing,
            "parsed": merged
        }, ensure_ascii=False)

    # If complete → run analyst with a synthetic query built from merged
    synthetic_query = f"price {merged['price']}, rent {merged['monthly_rent']}, costs {merged['monthly_costs']}"
    analysis = analyst_analyze(synthetic_query, plan_obj.get("needs", {}))
    log("Analyst results (continued)", analysis)

    # done with session (optional: keep for audit)
    SESSIONS.delete(session_id)

    # finalize pipeline as normal
    rag_hits = "\n".join(MEM.search(original_query, k=3)) or "no memory hits"
    min_yield = get_latest_min_yield(MIN_YIELD_PERCENT)
    return _finalize_pipeline(plan_obj, analysis, prefs_text, rag_hits, min_yield)
