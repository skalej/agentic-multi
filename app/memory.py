from typing import List, Optional
import json, os, re
import numpy as np
import faiss

from openai import OpenAI
from .config import OPENAI_API_KEY, OPENAI_EMBED_MODEL, MEM_INDEX_PATH, MEM_TEXTS_PATH

client = OpenAI(api_key=OPENAI_API_KEY)

class VectorMemory:
    def __init__(self, dim: int = 1536):
        self.dim = dim
        self.index = faiss.IndexFlatIP(dim)
        self.texts: List[str] = []
        self.embs: Optional[np.ndarray] = None

    def _embed(self, texts: List[str]) -> np.ndarray:
        resp = client.embeddings.create(model=OPENAI_EMBED_MODEL, input=texts)
        vecs = np.array([d.embedding for d in resp.data], dtype=np.float32)
        return vecs

    def add(self, text: str):
        vec = self._embed([text])
        if self.embs is None:
            self.embs = vec
        else:
            self.embs = np.vstack([self.embs, vec])
        self.index.add(vec)
        self.texts.append(text)

    def add_if_not_exists(self, text: str):
        if text not in self.texts:
            self.add(text)

    def add_many(self, notes: List[str]):
        if not notes:
            return
        vecs = self._embed(notes)
        if self.embs is None:
            self.embs = vecs
        else:
            self.embs = np.vstack([self.embs, vecs])
        self.index.add(vecs)
        self.texts.extend(notes)

    def search(self, query: str, k: int = 3) -> List[str]:
        if self.embs is None or len(self.texts) == 0:
            return []
        q = self._embed([query])
        D, I = self.index.search(q, k)
        return [self.texts[i] for i in I[0] if i != -1]

    def save(self):
        self.index = faiss.IndexFlatIP(self.dim)
        if self.embs is not None and len(self.embs) > 0:
            self.index.add(self.embs)
        faiss.write_index(self.index, MEM_INDEX_PATH)
        with open(MEM_TEXTS_PATH, "w", encoding="utf-8") as f:
            json.dump(self.texts, f, ensure_ascii=False, indent=2)

    def load(self):
        if os.path.exists(MEM_INDEX_PATH) and os.path.exists(MEM_TEXTS_PATH):
            try:
                with open(MEM_TEXTS_PATH, "r", encoding="utf-8") as f:
                    self.texts = json.load(f)
                if self.texts:
                    self.embs = self._embed(self.texts)
                    self.index = faiss.IndexFlatIP(self.dim)
                    self.index.add(self.embs)
            except Exception as e:
                print("⚠️ memory load failed:", e)

MEM = VectorMemory()
MEM.load()

# initial durable notes
if not MEM.texts:
    MEM.add("user_pref.min_yield = 7%")
    MEM.add("report_style = concise English with numbers and bullet points")
    MEM.add("baseline rule: if ROI < 7 then warn user")
    MEM.save()

def parse_min_yield_from_text(text: str) -> float | None:
    if not text:
        return None
    kw = re.search(r"(min(imum)?|at\s+least|threshold|>=|yield|roi)", text, flags=re.I)
    if not kw:
        return None
    m = re.search(r"([\d]+(?:\.\d+)?)\s*%", text, flags=re.I)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None

def get_latest_min_yield(default_value: float) -> float:
    for t in reversed(MEM.texts):
        m = re.search(r"user_pref\.min_yield\s*=\s*([\d.]+)\s*%", str(t))
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass
    return float(default_value)

def note_from_report(report_dict: dict) -> str:
    price = report_dict.get("price")
    rent = report_dict.get("monthly_rent")
    costs = report_dict.get("monthly_costs")
    roi = report_dict.get("roi", {})
    roi_pct = roi.get("roi_percent")
    guard = roi.get("guard")
    reco = report_dict.get("recommendation")
    critic = report_dict.get("critic_status")
    parts = [
        f"analysis.price={price}",
        f"rent={rent}",
        f"costs={costs}",
        f"roi={roi_pct}%",
        f"reco={reco}",
        f"critic={critic}"
    ]
    if guard:
        parts.append(f"guard={guard}")
    return " | ".join(str(p) for p in parts)
