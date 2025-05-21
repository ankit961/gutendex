from fastapi import FastAPI, Depends, Query, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.schemas import BookOut, BookListResponse, ChatBooksResponse, ChatRequest
from app.database import get_db
from app import schemas, crud
from fastapi import Body
from pydantic import BaseModel
from app.llm import extract_filter, summarize_results
from app.crud import get_books
import logging
from fastapi.responses import JSONResponse

app = FastAPI(
    title="Gutendex API",
    version="1.0.0",
    description="Query Project Gutenberg books by LLM-driven filters."
)

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    logging.info(f"404 Not Found: {request.url.path}")
    return JSONResponse(status_code=404, content={"detail": "The requested resource was not found."})

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    logging.error(f"500 Internal Server Error: {request.url.path} - {exc}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})

@app.exception_handler(504)
async def timeout_error_handler(request: Request, exc):
    logging.error(f"504 Gateway Timeout: {request.url.path} - {exc}")
    return JSONResponse(status_code=504, content={"detail": "The server timed out while processing your request."})

@app.get(
    "/books",
    response_model=schemas.BookListResponse,
    tags=["Books"]
)
def list_books(
    ids: Optional[List[int]] = Query(None, description="Gutenberg book IDs"),
    language: Optional[List[str]] = Query(None, description="Language codes (e.g., en, fr)"),
    mime_type: Optional[str] = Query(None, description="Format mime-type (e.g., text/plain)"),
    topic: Optional[List[str]] = Query(None, description="Search in subjects or bookshelves"),
    author: Optional[List[str]] = Query(None, description="Author name (partial match)"),
    title: Optional[List[str]] = Query(None, description="Book title (partial match)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(25, ge=1, le=100, description="Max records to return"),
    db: Session = Depends(get_db)
):
    """
    Retrieve a paginated list of books matching any combination of filters.
    Results are sorted by descending download count.
    """
    filters = {}
    if ids:       filters['ids'] = ids
    if language:  filters['language'] = language
    if mime_type: filters['mime_type'] = mime_type
    if topic:     filters['topic'] = topic
    if author:    filters['author'] = author
    if title:     filters['title'] = title

    try:
        total, books = crud.get_books(db, filters, skip, limit)
    except Exception as e:
        logging.error(f"Error fetching books: {e}")
        raise HTTPException(status_code=500, detail="Error fetching books from the database.")

    try:
        books_out = [BookOut.model_validate(b) for b in books]
    except Exception as e:
        logging.error(f"Error serializing books: {e}")
        raise HTTPException(status_code=500, detail="Error serializing book data.")

    return {"count": total, "results": books_out}

class ChatRequest(BaseModel):
    query: str

@app.post("/chat", response_model=ChatBooksResponse, tags=["AskDB"])
def chat(request: ChatRequest, db: Session = Depends(get_db)) -> ChatBooksResponse:
    """
    Handles chat queries, generates filters using LLM, fetches books, and summarizes results.
    """
    # 1) extract deterministic filter
    filters = extract_filter(request.query)
    if not filters:
        raise HTTPException(400, "Sorry, I couldn't parse any filters from that query.")

    # 2) normalize filter values to lists and correct types
    allowed = {"author", "title", "language", "topic", "mime_type", "ids"}
    cleaned: Dict[str, List[Any]] = {}
    for k, v in filters.items():
        if k in allowed:
            if k == "ids":
                if isinstance(v, int):
                    cleaned[k] = [v]
                elif isinstance(v, str) and v.isdigit():
                    cleaned[k] = [int(v)]
                elif isinstance(v, list):
                    cleaned[k] = [int(x) for x in v if isinstance(x, (int, str)) and str(x).isdigit()]
            elif isinstance(v, list):
                cleaned[k] = v
            else:
                cleaned[k] = [v]

    # --- PATCH: Try to extract language from the user query if not present in filters ---
    import re
    if "language" not in cleaned:
        # crude extraction: look for 'fr', 'en', etc. in the query
        m = re.search(r"\b([a-z]{2})\b", request.query.lower())
        if m:
            lang = m.group(1)
            if lang in {"fr", "en", "de", "es", "it"}:  # add more as needed
                cleaned["language"] = [lang]

    # 3) handle limit and sort from filters
    limit = filters.get("limit", 25)
    try:
        limit = int(limit)
    except Exception:
        limit = 25
    sort = filters.get("sort", None)

    # 4) fetch books
    total, books = crud.get_books(db, cleaned, skip=0, limit=limit)

    # 5) summarize
    summary = summarize_results(request.query, books)
    return ChatBooksResponse(
        filters=filters,
        count=len(books),
        results=[BookOut.model_validate(b) for b in books],
        summary=summary
    )

@app.get("/health")
def health():
    return {"status": "ok"}