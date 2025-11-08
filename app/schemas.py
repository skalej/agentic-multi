from typing import Optional, List, Any
from pydantic import BaseModel, Field, field_validator

class ROIResult(BaseModel):
    roi_percent: float = Field(..., ge=-100, le=100)
    annual_net_eur: float
    guard: Optional[str] = None

class LoanResult(BaseModel):
    monthly_payment_eur: float
    total_payment_eur: float
    total_interest_eur: float

class FinalReport(BaseModel):
    price: float
    monthly_rent: float
    monthly_costs: float
    roi: ROIResult
    loan: Optional[LoanResult] = None
    warnings: List[str] = []
    recommendation: str  # "BUY" | "HOLD" | "AVOID"
    critic_status: Optional[str] = None
    critic_reason: Optional[str] = None

    @field_validator("recommendation")
    @classmethod
    def valid_reco(cls, v):
        allowed = {"BUY", "HOLD", "AVOID"}
        if v not in allowed:
            raise ValueError(f"recommendation must be one of {allowed}")
        return v

class AnalysisRequest(BaseModel):
    query: str

class MemAddRequest(BaseModel):
    text: str

class MemSearchResponse(BaseModel):
    hits: List[str]

class PrefsMinYieldRequest(BaseModel):
    value: float

class ErrorResponse(BaseModel):
    error: str
    detail: Any = None
    parsed: Optional[dict] = None

class ContinueRequest(BaseModel):
    session_id: str
    reply_text: str

class RecoveryResponse(BaseModel):
    need_more_info: bool
    session_id: str | None = None
    ask: str | None = None
    missing: List[str] | None = None
    parsed: dict | None = None
