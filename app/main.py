from fastapi import FastAPI, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app import schemas, crud
from fastapi import FastAPI, Body
from pydantic import BaseModel
from app.llm import query_to_filter
from app.crud import get_books




app = FastAPI(
    title="Gutendex API",
    version="1.0.0",
    description="Query Project Gutenberg books by multiple filters."
)

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
        raise HTTPException(status_code=500, detail=str(e))

    return {"count": total, "results": books}

class ChatRequest(BaseModel):
    query: str

class ChatBooksResponse(BaseModel):
    filters: dict
    count: int
    results: list
    summary: str

@app.post("/chat", response_model=ChatBooksResponse, tags=["LLM"])
def chat(request: ChatRequest, db=Depends(get_db)):
    filters = query_to_filter(request.query)
    allowed = {"author", "title", "language", "topic", "mime_type", "ids"}
    filters = {k: v for k, v in filters.items() if k in allowed}
    count, books = get_books(db=db, **filters)
    summary = summarize_results(request.query, filters, books)
    return ChatBooksResponse(filters=filters, count=count, results=books, summary=summary)
