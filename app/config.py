import os
from dotenv import load_dotenv

load_dotenv()

def _get_float(name: str, default: float) -> float:
    val = os.getenv(name, str(default))
    try:
        return float(str(val).strip())
    except Exception:
        return default

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")

MIN_YIELD_PERCENT = _get_float("MIN_YIELD_PERCENT", 7.0)

MEM_INDEX_PATH = os.getenv("MEM_INDEX_PATH", "mem.index")
MEM_TEXTS_PATH = os.getenv("MEM_TEXTS_PATH", "mem_texts.json")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not set in .env")
