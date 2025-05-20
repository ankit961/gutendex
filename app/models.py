from sqlalchemy import (
    Table, Column, Integer, String, ForeignKey, SmallInteger
)
from sqlalchemy.orm import relationship
from app.database import Base

book_authors = Table(
    'books_book_authors', Base.metadata,
    Column('book_id', ForeignKey('books_book.id'), primary_key=True),
    Column('author_id', ForeignKey('books_author.id'), primary_key=True),
)

book_subjects = Table(
    'books_book_subjects', Base.metadata,
    Column('book_id', ForeignKey('books_book.id'), primary_key=True),
    Column('subject_id', ForeignKey('books_subject.id'), primary_key=True),
)

book_bookshelves = Table(
    'books_book_bookshelves', Base.metadata,
    Column('book_id', ForeignKey('books_book.id'), primary_key=True),
    Column('bookshelf_id', ForeignKey('books_bookshelf.id'), primary_key=True),
)

book_languages = Table(
    'books_book_languages', Base.metadata,
    Column('book_id', ForeignKey('books_book.id'), primary_key=True),
    Column('language_id', ForeignKey('books_language.id'), primary_key=True),
)

class Author(Base):
    __tablename__ = 'books_author'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    birth_year = Column(SmallInteger)
    death_year = Column(SmallInteger)
    books = relationship('Book', secondary=book_authors, back_populates='authors')

class Subject(Base):
    __tablename__ = 'books_subject'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    books = relationship('Book', secondary=book_subjects, back_populates='subjects')

class Bookshelf(Base):
    __tablename__ = 'books_bookshelf'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    books = relationship('Book', secondary=book_bookshelves, back_populates='bookshelves')

class Language(Base):
    __tablename__ = 'books_language'
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(8), nullable=False)
    books = relationship('Book', secondary=book_languages, back_populates='languages')

class Format(Base):
    __tablename__ = 'books_format'
    id = Column(Integer, primary_key=True, index=True)
    mime_type = Column(String(100), nullable=False)
    url = Column(String(2048), nullable=False)
    book_id = Column(Integer, ForeignKey('books_book.id'), nullable=False)
    book = relationship('Book', back_populates='formats')

class Book(Base):
    __tablename__ = 'books_book'
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(1024), nullable=False)
    download_count = Column(Integer, nullable=True)

    authors = relationship('Author', secondary=book_authors, back_populates='books')
    subjects = relationship('Subject', secondary=book_subjects, back_populates='books')
    bookshelves = relationship('Bookshelf', secondary=book_bookshelves, back_populates='books')
    languages = relationship('Language', secondary=book_languages, back_populates='books')
    formats = relationship('Format', back_populates='book')
