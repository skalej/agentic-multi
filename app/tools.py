from typing import Dict, Any, Optional

def guard_price(price: float) -> Optional[str]:
    if price < 20000 or price > 500000:
        return "⚠️ Price out of safe bounds (20k–500k)."
    return None

def roi_calc(price: float, monthly_rent: float, monthly_costs: float) -> Dict[str, Any]:
    warn = guard_price(price)
    annual_net = (monthly_rent - monthly_costs) * 12
    roi = (annual_net / price) * 100 if price > 0 else 0.0
    return {
        "roi_percent": round(roi, 2),
        "annual_net_eur": round(annual_net, 2),
        "guard": warn
    }

def loan_calc(principal: float, annual_rate_percent: float, years: int) -> Dict[str, Any]:
    if principal <= 0 or years <= 0 or not (0 < annual_rate_percent < 50):
        raise ValueError("Invalid loan inputs.")
    r = annual_rate_percent / 100.0 / 12.0
    n = years * 12
    m = principal * (r * (1 + r) ** n) / ((1 + r) ** n - 1)
    total = m * n
    return {
        "monthly_payment_eur": round(m, 2),
        "total_payment_eur": round(total, 2),
        "total_interest_eur": round(total - principal, 2)
    }

ALLOWED_EMAIL_DOMAINS = {"example.com", "mycompany.de"}
def email_sender(to_email: str, subject: str, body: str) -> Dict[str, Any]:
    domain = to_email.split("@")[-1].lower()
    if domain not in ALLOWED_EMAIL_DOMAINS:
        return {"status": "blocked", "reason": "unauthorized domain"}
    return {"status": "sent", "to": to_email, "subject": subject}

def recommendation_from_roi(roi_percent: float, min_yield: float) -> str:
    if roi_percent >= (min_yield + 1):
        return "BUY"
    elif roi_percent >= (min_yield - 1):
        return "HOLD"
    return "AVOID"
