from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import Dict, List

from app.models import Book, Author, Subject, Bookshelf, Format, Language

def get_books(
    db: Session,
    filters: Dict[str, List[str]],
    skip: int = 0,
    limit: int = 25
) -> (int, List[Book]):
    """
    Returns (total_count, list_of_books) matching the given filters.
    """
    query = db.query(Book)

    # Apply filters
    if 'ids' in filters:
        query = query.filter(Book.id.in_(filters['ids']))

    if 'language' in filters:
        query = query.filter(Book.languages.any(Language.code.in_(filters['language'])))

    if 'mime_type' in filters:
        query = query.filter(Book.formats.any(Format.mime_type == filters['mime_type']))

    if 'topic' in filters:
        for topic in filters['topic']:
            query = query.filter(
                or_(
                    Book.subjects.any(Subject.name.ilike(f"%{topic}%")),
                    Book.bookshelves.any(Bookshelf.name.ilike(f"%{topic}%"))
                )
            )

    if 'author' in filters:
        for name in filters['author']:
            query = query.filter(Book.authors.any(Author.name.ilike(f"%{name}%")))

    if 'title' in filters:
        for t in filters['title']:
            query = query.filter(Book.title.ilike(f"%{t}%"))

    # --- Count unique books ---
    total = query.with_entities(Book.id).distinct().count()

    # --- Get paginated unique IDs in order ---
    subq = (
        query.with_entities(Book.id, Book.download_count)
        .order_by(Book.download_count.desc().nullslast())
        .distinct()
        .offset(skip)
        .limit(limit)
        .subquery()
    )
    # Now fetch Book objects in the same order as subq
    books = (
        db.query(Book)
        .join(subq, Book.id == subq.c.id)
        .order_by(subq.c.download_count.desc().nullslast())
        .all()
    )

    return total, books