import json
from fastapi import FastAPI, HTTPException, Query
from .schemas import AnalysisRequest, FinalReport, MemAddRequest, MemSearchResponse, PrefsMinYieldRequest
from .orchestrator import run_analysis
from .memory import MEM, note_from_report, parse_min_yield_from_text, get_latest_min_yield
from .config import MIN_YIELD_PERCENT

app = FastAPI(title="Agentic Multi-Agent Real Estate")

@app.post("/analyze")
def analyze(inp: AnalysisRequest):
    raw = run_analysis(inp.query)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as je:
        raise HTTPException(422, detail=f"Reporter did not return valid JSON: {je}. Raw: {raw[:300]}")

    try:
        report = FinalReport(**data)
    except Exception as e:
        raise HTTPException(422, detail=f"Schema validation failed: {str(e)}")
    return report

@app.post("/mem/add")
def mem_add(req: MemAddRequest):
    MEM.add_if_not_exists(req.text)
    normalized = None
    try:
        val = parse_min_yield_from_text(req.text)
        if val is not None:
            normalized = f"user_pref.min_yield = {val}%"
            MEM.add_if_not_exists(normalized)
        MEM.save()
    except Exception as e:
        print("memory save error:", e)
    return {"ok": True, "added": req.text, "normalized_min_yield": normalized}

@app.get("/mem/search", response_model=MemSearchResponse)
def mem_search(q: str = Query(...), k: int = 3):
    hits = MEM.search(q, k=k)
    return MemSearchResponse(hits=hits)

@app.post("/prefs/min_yield")
def set_min_yield(req: PrefsMinYieldRequest):
    canonical = f"user_pref.min_yield = {float(req.value)}%"
    MEM.add_if_not_exists(canonical)
    MEM.save()
    return {"ok": True, "set": canonical}

@app.get("/prefs/effective")
def get_effective_prefs():
    eff = get_latest_min_yield(MIN_YIELD_PERCENT)
    return {"min_yield_percent": eff}
