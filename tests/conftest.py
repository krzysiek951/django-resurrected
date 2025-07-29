from __future__ import annotations

from datetime import datetime

import pytest
from model_bakery import baker
from test_app import models


def assert_is_active(*objs):
    for obj in objs:
        obj.refresh_from_db()
        assert obj.is_removed is False
        assert obj.removed_at is None


def assert_is_removed(*objs, removed_at: datetime | None = None):
    for obj in objs:
        obj.refresh_from_db()
        assert obj.is_removed
        assert obj.removed_at if removed_at is None else obj.removed_at == removed_at


@pytest.fixture
def make_authors():
    return lambda quantity=3, **kwargs: baker.make(
        models.Author, _quantity=quantity, **kwargs
    )


@pytest.fixture
def make_author_profile():
    return lambda author, **kwargs: baker.make(
        models.AuthorProfile, author=author, **kwargs
    )


@pytest.fixture
def make_book():
    return lambda author, **kwargs: baker.make(models.Book, author=author, **kwargs)


@pytest.fixture
def make_book_category():
    return lambda **kwargs: baker.make(models.BookCategory, **kwargs)


@pytest.fixture
def make_book_meta():
    return lambda book, **kwargs: baker.make(models.BookMeta, book=book, **kwargs)


@pytest.fixture
def test_author(make_authors):
    return make_authors(quantity=1)[0]


@pytest.fixture
def author_with_profile(test_author, make_author_profile):
    profile = make_author_profile(author=test_author)
    return test_author, profile


@pytest.fixture
def author_with_books(test_author, make_book):
    books = make_book(author=test_author, _quantity=2)
    return test_author, books


@pytest.fixture
def book_with_category(test_author, make_book, make_book_category):
    book = make_book(test_author)
    category = make_book_category()
    book.categories.add(category)
    return book, category


@pytest.fixture
def author_with_nested_relations(
    author_with_profile, book_with_category, make_book_meta
):
    author, profile = author_with_profile
    book, category = book_with_category
    book_meta = make_book_meta(book)
    book.author = author
    book.save()
    return author, profile, book, book_meta, category
