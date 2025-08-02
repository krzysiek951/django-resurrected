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


def remove_objs(*objs):
    for obj in objs:
        obj.remove()
    assert_is_removed(*objs)


@pytest.fixture
def make_author():
    return lambda **kwargs: baker.make(models.Author, **kwargs)


@pytest.fixture
def make_author_profile():
    return lambda author, **kwargs: baker.make(
        models.AuthorProfile, author=author, **kwargs
    )


@pytest.fixture
def make_book():
    return lambda author, **kwargs: baker.make(models.Book, author=author, **kwargs)


@pytest.fixture
def make_book_meta():
    return lambda book, **kwargs: baker.make(models.BookMeta, book=book, **kwargs)


@pytest.fixture
def make_book_category():
    return lambda **kwargs: baker.make(models.BookCategory, **kwargs)


@pytest.fixture
def test_author(make_author):
    return make_author()


@pytest.fixture
def author_with_profile(make_author, make_author_profile):
    author = make_author()
    profile = make_author_profile(author=author)
    return author, profile


@pytest.fixture
def author_with_books(make_author, make_book):
    author = make_author()
    books = make_book(author=author, _quantity=2)
    return author, books


@pytest.fixture
def book_with_category(make_author, make_book, make_book_category):
    book = make_book(author=make_author())
    category = make_book_category()
    book.categories.add(category)
    return book, category


@pytest.fixture
def make_author_with_all_relations(
    make_author, make_author_profile, make_book, make_book_meta, make_book_category
):
    def _make_author_with_all_relations():
        author = make_author()
        profile = make_author_profile(author=author)
        book_1, book_2 = make_book(author=author, _quantity=2)
        book_meta_1 = make_book_meta(book_1)
        book_meta_2 = make_book_meta(book_2)
        category_1, category_2 = make_book_category(_quantity=2)
        book_1.categories.add(category_1)
        book_2.categories.add(category_2)
        return author, (
            profile,
            book_1,
            book_2,
            book_meta_1,
            book_meta_2,
            category_1,
            category_2,
        )

    return _make_author_with_all_relations
