from pydantic import BaseModel
from typing import List, Optional

class AuthorOut(BaseModel):
    id: int
    name: str
    birth_year: Optional[int]
    death_year: Optional[int]

    model_config = {"from_attributes": True}

class SubjectOut(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}

class BookshelfOut(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}

class LanguageOut(BaseModel):
    id: int
    code: str

    model_config = {"from_attributes": True}

class FormatOut(BaseModel):
    mime_type: str
    url: str

    model_config = {"from_attributes": True}

class BookOut(BaseModel):
    id: int
    title: Optional[str] = None
    download_count: int
    authors: List[AuthorOut]
    subjects: List[SubjectOut]
    bookshelves: List[BookshelfOut]
    languages: List[LanguageOut]
    formats: List[FormatOut]

    model_config = {"from_attributes": True}


class BookListResponse(BaseModel):
    count: int
    results: List[BookOut]
