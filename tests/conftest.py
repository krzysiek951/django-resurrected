from __future__ import annotations

from datetime import datetime

import pytest
from freezegun import freeze_time
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
    def make_authors(quantity: int = 3):
        authors = baker.make(models.Author, _quantity=quantity)
        for author in authors:
            assert_is_active(author)
        return authors

    return make_authors


@pytest.fixture
def make_author_profile():
    return lambda author: baker.make(models.AuthorProfile, author=author)


@pytest.fixture
def make_book():
    return lambda author: baker.make(models.Book, author=author)


@pytest.fixture
def make_book_category():
    return lambda: baker.make(models.BookCategory)


@pytest.fixture
def make_book_meta():
    return lambda book: baker.make(models.BookMeta, book=book)


@pytest.fixture
def test_author(make_authors):
    return make_authors(quantity=1)[0]


@pytest.fixture
@freeze_time("2025-05-01")
def removed_author(test_author):
    test_author.remove()
    assert_is_removed(test_author)
    return test_author


@pytest.fixture
def author_with_profile(test_author, make_author_profile):
    profile = make_author_profile(author=test_author)
    assert_is_active(test_author, profile)
    return test_author, profile


@pytest.fixture
@freeze_time("2025-05-01")
def removed_author_with_removed_profile(author_with_profile):
    author, profile = author_with_profile
    author.remove()
    assert_is_removed(author, profile)
    return author, profile


@pytest.fixture
def author_with_books(test_author, make_book):
    book1 = make_book(author=test_author)
    book2 = make_book(author=test_author)
    assert_is_active(test_author, book1, book2)
    return test_author, [book1, book2]


@pytest.fixture
@freeze_time("2025-05-01")
def removed_author_with_removed_books(author_with_books):
    author, books = author_with_books
    author.remove()
    assert_is_removed(author, *books)
    return author, books


@pytest.fixture
def book_with_category(test_author, make_book, make_book_category):
    book = make_book(test_author)
    category = make_book_category()
    book.categories.add(category)
    assert_is_active(book, category)
    return book, category


@pytest.fixture
@freeze_time("2025-05-01")
def removed_book_with_category(book_with_category):
    book, category = book_with_category
    book.remove()
    assert_is_removed(book)
    assert_is_active(category)
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


@pytest.fixture
@freeze_time("2025-05-01")
def removed_author_with_nested_relations(author_with_nested_relations):
    author, profile, book, book_meta, category = author_with_nested_relations
    author.remove()
    assert_is_removed(author, profile, book, book_meta)
    assert_is_active(category)
    return author, profile, book, book_meta, category
