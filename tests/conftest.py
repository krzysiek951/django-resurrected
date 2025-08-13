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


def assert_is_remove_targeting_objects_for_deletion(
    model_or_queryset, remove_result, through_models=None
):
    num_deleted, num_deleted_per_model = model_or_queryset.hard_delete()
    for model in through_models or []:
        count = num_deleted_per_model.pop(model)
        num_deleted -= count
    assert remove_result == (num_deleted, num_deleted_per_model)


def run_remove_test(
    obj_or_queryset_to_remove,
    expected_removed=None,
    through_models=None,
    expected_active=None,
):
    result = obj_or_queryset_to_remove.remove()

    if expected_active:
        assert_is_active(*expected_active)
    if expected_removed:
        assert_is_removed(*expected_removed)
    assert_is_remove_targeting_objects_for_deletion(
        obj_or_queryset_to_remove, result, through_models
    )


def run_restore_test(
    obj_or_queryset_to_restore,
    with_related=False,
    expected_active=None,
    expected_removed=None,
):
    obj_or_queryset_to_restore.restore(with_related=with_related)

    if expected_active:
        assert_is_active(*expected_active)
    if expected_removed:
        assert_is_removed(*expected_removed)


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
def make_profile_meta():
    return lambda profile, **kwargs: baker.make(
        models.ProfileMeta, profile=profile, **kwargs
    )


@pytest.fixture
def make_book():
    return lambda author, **kwargs: baker.make(models.Book, author=author, **kwargs)


@pytest.fixture
def make_book_restrict():
    return lambda author, **kwargs: baker.make(
        models.BookRestrict, author=author, **kwargs
    )


@pytest.fixture
def make_book_protect():
    return lambda author, **kwargs: baker.make(
        models.BookProtect, author=author, **kwargs
    )


@pytest.fixture
def make_book_nullable():
    return lambda author, **kwargs: baker.make(
        models.BookNullable, author=author, **kwargs
    )


@pytest.fixture
def make_book_meta():
    return lambda book, **kwargs: baker.make(models.BookMeta, book=book, **kwargs)


@pytest.fixture
def make_book_category():
    return lambda **kwargs: baker.make(models.BookCategory, **kwargs)


@pytest.fixture
def active_author(make_author):
    return make_author()


class ManyToManyCascadeRelationTestBase:
    @pytest.fixture
    def active_books_with_rels(
        self, make_author, make_book, make_book_meta, make_book_category
    ):
        author = make_author()
        cat_1, cat_2, cat_3 = make_book_category(_quantity=3)
        book_1, book_2, book_3 = make_book(author=author, _quantity=3)
        book_1.categories.add(cat_1)
        book_2.categories.add(cat_2, cat_3)
        book_1_meta = make_book_meta(book=book_1)
        book_2_meta = make_book_meta(book=book_2)
        return (
            (book_1, book_2, book_3),
            (book_1_meta, book_2_meta),
            (cat_1, cat_2, cat_3),
        )

    @pytest.fixture
    def removed_books_with_rels(self, active_books_with_rels):
        books, book_metas, categories = active_books_with_rels
        remove_objs(*books, *categories)
        assert_is_removed(*books, *book_metas, *categories)
        return books, book_metas, categories


class ManyToOneCascadeRelationTestBase:
    @pytest.fixture
    def active_author_with_rels(self, make_author, make_book, make_book_meta):
        author = make_author()
        book_1, book_2, book_3 = make_book(author=author, _quantity=3)
        book_1_meta = make_book_meta(book=book_1)
        book_2_meta = make_book_meta(book=book_2)
        assert_is_active(
            author, book_1, book_1.bookmeta, book_2, book_2.bookmeta, book_3
        )
        return author, (book_1, book_2, book_3), (book_1_meta, book_2_meta)

    @pytest.fixture
    def removed_author_with_rels(self, active_author_with_rels):
        author, books, book_metas = active_author_with_rels
        author.remove()
        assert_is_removed(author, *books, *book_metas)
        return author, books, book_metas


class ManyToOneProtectRelationTestBase:
    @pytest.fixture
    def active_author_with_rels(self, make_author, make_book_protect):
        author = make_author()
        book_1, book_2 = make_book_protect(author=author, _quantity=2)
        assert_is_active(author, book_1, book_2)
        return author, (book_1, book_2)


class ManyToOneRestrictRelationTestBase:
    @pytest.fixture
    def active_author_with_rels(self, make_author, make_book_restrict):
        author = make_author()
        book_1, book_2 = make_book_restrict(author=author, _quantity=2)
        assert_is_active(author, book_1, book_2)
        return author, (book_1, book_2)


class OneToOneCascadeRelationTestBase:
    @pytest.fixture
    def active_author(self, make_author, make_author_profile, make_profile_meta):
        author = make_author()
        profile = make_author_profile(author=author)
        profile_meta = make_profile_meta(profile=profile)
        assert_is_active(author, profile, profile_meta)
        return author

    @pytest.fixture
    def removed_author(self, active_author):
        active_author.remove()
        assert_is_removed(
            active_author, active_author.profile, active_author.profile.profilemeta
        )
        return active_author
