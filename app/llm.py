"""
llm.py

A robust LLM-driven filter-and-summary module for Gutendex.

Features:
- Thread-safe model initialization
- Controlled sampling (temperature, top-p, top-k, repetition penalty)
- Multi-candidate generation with best-candidate selection
- Explicit handling for 'most downloaded', 'latest', and 'top N' queries
- Sanitization and JSON-only output between clear markers
- Example usage at bottom
"""
import json
import logging
import re
from threading import Lock
from typing import Any, Dict, List, Optional

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, GenerationConfig

from app.config import settings

logger = logging.getLogger(__name__)

# Thread-safe singletons
_model: Optional[AutoModelForCausalLM] = None
_tokenizer: Optional[AutoTokenizer] = None
_lock = Lock()


def _device() -> str:
    """Utility: returns 'cuda' if available, else 'cpu'."""
    return "cuda" if torch.cuda.is_available() else "cpu"


def init_model():
    """
    Load model and tokenizer once, in a thread-safe manner.
    """
    global _model, _tokenizer
    with _lock:
        if _model is None or _tokenizer is None:
            _tokenizer = AutoTokenizer.from_pretrained(
                settings.LLM_MODEL_PATH, trust_remote_code=True
            )
            _model = AutoModelForCausalLM.from_pretrained(
                settings.LLM_MODEL_PATH,
                trust_remote_code=True,
                torch_dtype=(torch.float16 if torch.cuda.is_available() else torch.float32),
            ).to(_device())


def generate_text(
    prompt: str,
    max_new_tokens: int = 128,
    temperature: float = 0.7,
    top_p: float = 0.9,
    top_k: int = 50,
    repetition_penalty: float = 1.2,
    num_return_sequences: int = 3
) -> List[str]:
    """
    Generate multiple sampled outputs from the model.
    """
    init_model()
    inputs = _tokenizer(prompt, return_tensors='pt').to(_device())
    gen_cfg = GenerationConfig(
        max_new_tokens=max_new_tokens,
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
        repetition_penalty=repetition_penalty,
        do_sample=True,
        num_return_sequences=num_return_sequences,
        eos_token_id=_tokenizer.eos_token_id
    )
    with torch.no_grad():
        outputs = _model.generate(**inputs, generation_config=gen_cfg)
    return [_tokenizer.decode(out, skip_special_tokens=True) for out in outputs]


def sanitize_filter(filt: Dict[str, Any], query: str) -> Dict[str, Any]:
    """
    Keep only keys that appear explicitly in query (or sort/limit).
    """
    allowed = {'author', 'title', 'language', 'topic', 'mime_type', 'ids', 'sort', 'limit', 'download_count'}
    query_lower = query.lower()
    explicit = set()
    for k in allowed:
        if k in ['sort', 'limit']:
            if any(w in query_lower for w in ('most downloaded', 'latest', 'top')):
                explicit.add(k)
        elif k == 'ids' and ('id' in query_lower or 'ids' in query_lower):
            explicit.add(k)
        elif k in query_lower:
            explicit.add(k)
    if 'download' in query_lower:
        explicit.add('download_count')
    result = {}
    for k, v in filt.items():
        if k in explicit:
            if k == 'ids':
                if isinstance(v, int):
                    result[k] = [v]
                elif isinstance(v, str) and v.isdigit():
                    result[k] = [int(v)]
                elif isinstance(v, list):
                    result[k] = [int(x) for x in v if isinstance(x, (int, str)) and str(x).isdigit()]
            elif k == 'limit':
                try:
                    result[k] = int(v)
                except Exception:
                    continue
            else:
                result[k] = v
    return result


def extract_filter(query: str) -> Dict[str, Any]:
    """
    Convert a natural-language query into a Gutendex filter dict.
    Handles:
      - "most downloaded" / "top N" → sort:download_count desc, limit:N
      - "latest" / "latest N" → sort:latest, limit:N
      - Otherwise, uses LLM to produce JSON between <FILTER>…</FILTER>
    """
    q = query.strip()
    if re.search(r"\bmost downloaded\b|\btop \d+\b", q, re.IGNORECASE):
        m = re.search(r"top (\d+)", q, re.IGNORECASE)
        n = int(m.group(1)) if m else 1
        return {"sort": "download_count:desc", "limit": n}
    if re.search(r"\blatest\b", q, re.IGNORECASE):
        m = re.search(r"latest (\d+)", q, re.IGNORECASE)
        n = int(m.group(1)) if m else 1
        return {"sort": "latest", "limit": n}
    prompt = (
        "Allowed keys: author, title, language, topic, mime_type, ids, sort, limit, download_count.\n"
        "Output only one valid JSON object, no extra text, between <<<FILTER>>> and <<<END>>>.\n"
        f"Query: {q}\n<<<FILTER>>>"
    )
    try:
        candidates = generate_text(prompt, max_new_tokens=120, temperature=0.2, num_return_sequences=2)
        for raw in candidates:
            m = re.search(r"<<<FILTER>>>(\{.*?\})<<<END>>>", raw, re.DOTALL)
            if m:
                try:
                    filt = json.loads(m.group(1))
                    return sanitize_filter(filt, query)
                except Exception:
                    continue
        for raw in candidates:
            m = re.search(r"(\{.*\})", raw, re.DOTALL)
            if m:
                try:
                    filt = json.loads(m.group(1))
                    return sanitize_filter(filt, query)
                except Exception:
                    continue
    except Exception as e:
        logger.error(f"Failed to generate filter: {e}")
    return {}


def summarize_results(query: str, books: List[Any]) -> str:
    """
    Summarize the overall search result into a concise 1-2 sentence description,
    without listing individual books.
    """
    if not books:
        return "No books matched your criteria."
    book_titles = ', '.join([getattr(b, 'title', None) for b in books if getattr(b, 'title', None)])
    author_names = ', '.join({getattr(a, 'name', None) for b in books for a in getattr(b, 'authors', []) if getattr(a, 'name', None)})
    prompt = (
        f"There {'is' if len(books)==1 else 'are'} {len(books)} book{'s' if len(books)!=1 else ''}"
        + (f" by {author_names}" if author_names else "")
        + (f': "{book_titles}"' if book_titles else "")
        + ". Write a 1-2 sentence summary of this result."
    )
    try:
        cands = generate_text(prompt, max_new_tokens=80, temperature=0.8)
        logger.info(f"LLM summary candidates: {cands}")
        valid = []
        for c in cands:
            # Remove the prompt from the start if present
            if c.startswith(prompt):
                c = c[len(prompt):].lstrip("\n: ")
            if len(c.strip()) > 20:
                valid.append(c.strip())
        if valid:
            return max(valid, key=len)
    except Exception as e:
        logger.error(f"Summary failed: {e}")
    return f"Found {len(books)} books matching your query."


