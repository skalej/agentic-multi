from typing import Tuple, List

def review(roi_percent: float, warnings: List[str], min_yield: float) -> Tuple[str, str | None]:
    if float(roi_percent) < float(min_yield):
        return "rejected", f"ROI {roi_percent}% is below the minimum yield of {min_yield}%."
    if any("⚠️" in w for w in warnings):
        return "rejected", "Safety/guardrail warning present."
    return "approved", None
