from datetime import datetime
from unittest.mock import patch

import pytest
import pytz
from django.db.models import ProtectedError
from django.db.models import RestrictedError
from freezegun.api import freeze_time
from test_app.models import Author

from django_resurrected.managers import ActiveObjectsQuerySet
from django_resurrected.managers import AllObjectsQuerySet
from django_resurrected.managers import RemovedObjectsQuerySet
from tests.conftest import ManyToManyCascadeRelationTestBase
from tests.conftest import ManyToOneCascadeRelationTestBase
from tests.conftest import ManyToOneProtectRelationTestBase
from tests.conftest import ManyToOneRestrictRelationTestBase
from tests.conftest import OneToOneCascadeRelationTestBase
from tests.conftest import assert_is_active
from tests.conftest import assert_is_removed
from tests.conftest import run_remove_test
from tests.conftest import run_restore_test


@pytest.mark.django_db
class TestActiveObjectsQuerySet:
    @freeze_time("2025-05-01")
    def test_remove(self, make_author):
        authors = make_author(_quantity=3)
        assert_is_active(*authors)
        Author.active_objects.all().remove()
        assert_is_removed(*authors, removed_at=datetime(2025, 5, 1, tzinfo=pytz.utc))

    @patch.object(ActiveObjectsQuerySet, "remove")
    def test_delete(self, remove_mock):
        Author.active_objects.all().delete()
        remove_mock.assert_called_once()


@pytest.mark.django_db
class TestRemovedObjectsQuerySet:
    @patch.object(RemovedObjectsQuerySet, "purge")
    def test_delete(self, purge_mock, active_author):
        Author.removed_objects.all().delete()
        purge_mock.assert_called_once()

    @freeze_time("2025-05-01")
    def test_purge(self, make_author):
        author_1, author_2, author_3 = make_author(_quantity=3)
        author_1.remove()
        assert_is_active(author_2, author_3)
        assert_is_removed(author_1)

        with freeze_time("2025-05-31"):
            Author.removed_objects.all().purge()
        assert Author.objects.filter(id=author_1.id).exists()
        assert Author.objects.count() == 3

        with freeze_time("2025-06-01"):
            Author.removed_objects.all().purge()
        assert Author.objects.filter(id=author_1.id).exists() is False
        assert Author.objects.count() == 2

    @freeze_time("2025-05-01")
    def test_expired(self, make_author):
        author_1, author_2, author_3 = make_author(_quantity=3)
        author_1.remove()
        assert_is_active(author_2, author_3)
        assert_is_removed(author_1)

        assert Author.removed_objects.all().expired().count() == 0

        with freeze_time("2025-05-31"):
            assert Author.removed_objects.all().expired().count() == 0

        with freeze_time("2025-06-01"):
            assert Author.removed_objects.all().expired().count() == 1


@pytest.mark.django_db
class TestAllObjectsQuerySet:
    @patch.object(AllObjectsQuerySet, "remove")
    def test_delete(self, remove_mock):
        Author.objects.all().delete()
        remove_mock.assert_called_once()


@pytest.mark.django_db
class TestManyToManyCascadeRelation(ManyToManyCascadeRelationTestBase):
    def test_remove_called_by_reverse_related(self, active_books_with_rels):
        books, book_metas, categories = active_books_with_rels
        cat_1, cat_2, cat_3 = categories
        model = cat_2._meta.model
        run_remove_test(
            model.objects.filter(id=cat_2.id),
            expected_removed=[cat_2],
            expected_active=[*books, *book_metas, cat_1, cat_3],
            through_models=["test_app.Book_categories"],
        )

    def test_remove_called_by_forward_related(self, active_books_with_rels):
        books, book_metas, categories = active_books_with_rels
        book_1, book_2, book_3 = books
        model = book_2._meta.model
        run_remove_test(
            model.objects.filter(id=book_2.id),
            expected_removed=[book_2, book_2.bookmeta],
            expected_active=[book_1, book_1.bookmeta, book_3, *categories],
            through_models=["test_app.Book_categories"],
        )

    def test_restore_called_by_reverse_related(self, removed_books_with_rels):
        books, book_metas, categories = removed_books_with_rels
        cat_1, cat_2, cat_3 = categories
        model = cat_2._meta.model
        run_restore_test(
            model.objects.filter(id=cat_2.id),
            expected_active=[cat_2],
            expected_removed=[*books, *book_metas, cat_1, cat_3],
        )

    def test_restore_with_related_called_by_reverse_related(
        self, removed_books_with_rels
    ):
        books, book_metas, categories = removed_books_with_rels
        cat_1, cat_2, cat_3 = categories
        model = cat_2._meta.model
        run_restore_test(
            model.objects.filter(id=cat_2.id),
            with_related=True,
            expected_active=[cat_2],
            expected_removed=[*books, *book_metas, cat_1, cat_3],
        )

    def test_restore_called_by_forward_related(self, removed_books_with_rels):
        books, book_metas, categories = removed_books_with_rels
        book_1, book_2, book_3 = books
        model = book_2._meta.model
        run_restore_test(
            model.objects.filter(id=book_2.id),
            expected_active=[book_2],
            expected_removed=[
                book_1,
                book_1.bookmeta,
                book_2.bookmeta,
                book_3,
                *categories,
            ],
        )

    def test_restore_with_related_called_by_forward_related(
        self, removed_books_with_rels
    ):
        books, book_metas, categories = removed_books_with_rels
        book_1, book_2, book_3 = books
        model = book_2._meta.model
        run_restore_test(
            model.objects.filter(id=book_2.id),
            with_related=True,
            expected_active=[book_2, book_2.bookmeta],
            expected_removed=[book_1, book_1.bookmeta, book_3, *categories],
        )


@pytest.mark.django_db
class TestManyToOneCascadeRelation(ManyToOneCascadeRelationTestBase):
    def test_remove_called_by_reverse_related(self, active_author_with_rels):
        author, books, book_metas = active_author_with_rels
        model = author._meta.model
        run_remove_test(
            model.objects.filter(id=author.id),
            expected_removed=[author, *books, *book_metas],
        )

    def test_remove_called_by_forward_related(self, active_author_with_rels):
        author, books, book_metas = active_author_with_rels
        book_1, book_2, book_3 = books
        model = book_2._meta.model
        run_remove_test(
            model.objects.filter(id=book_2.id),
            expected_removed=[book_2, book_2.bookmeta],
            expected_active=[author, book_1, book_1.bookmeta, book_3],
        )

    def test_restore_called_by_reverse_related(self, removed_author_with_rels):
        author, books, book_metas = removed_author_with_rels
        model = author._meta.model
        run_restore_test(
            model.objects.filter(id=author.id),
            expected_active=[author],
            expected_removed=[*books, *book_metas],
        )

    def test_restore_with_related_called_by_reverse_related(
        self, removed_author_with_rels
    ):
        author, books, book_metas = removed_author_with_rels
        model = author._meta.model
        run_restore_test(
            model.objects.filter(id=author.id),
            with_related=True,
            expected_active=[author, *books, *book_metas],
        )

    def test_restore_called_by_forward_related(self, removed_author_with_rels):
        author, books, book_metas = removed_author_with_rels
        book_1, book_2, book_3 = books
        model = book_2._meta.model
        run_restore_test(
            model.objects.filter(id=book_2.id),
            expected_active=[author, book_2],
            expected_removed=[book_1, book_1.bookmeta, book_2.bookmeta, book_3],
        )

    def test_restore_with_related_called_by_forward_related(
        self, removed_author_with_rels
    ):
        author, books, book_metas = removed_author_with_rels
        book_1, book_2, book_3 = books
        model = book_2._meta.model
        run_restore_test(
            model.objects.filter(id=book_2.id),
            with_related=True,
            expected_active=[author, book_2, book_2.bookmeta],
            expected_removed=[book_1, book_1.bookmeta, book_3],
        )


@pytest.mark.django_db
class TestManyToOneProtectRelation(ManyToOneProtectRelationTestBase):
    def test_remove_called_by_reverse_related(self, active_author_with_rels):
        author, _ = active_author_with_rels
        model = author._meta.model
        with pytest.raises(ProtectedError):
            model.objects.filter(id=author.id).remove()

    def test_test_remove_called_by_forward_related(self, active_author_with_rels):
        author, books = active_author_with_rels
        book_1, book_2 = books
        model = book_2._meta.model
        run_remove_test(
            model.objects.filter(id=book_2.id),
            expected_removed=[book_2],
            expected_active=[author, book_1],
        )


@pytest.mark.django_db
class TestManyToOneRestrictRelation(ManyToOneRestrictRelationTestBase):
    def test_remove_called_by_reverse_related(self, active_author_with_rels):
        author, books = active_author_with_rels
        model = author._meta.model
        with pytest.raises(RestrictedError):
            model.objects.filter(id=author.id).remove()

    def test_test_remove_called_by_forward_related(self, active_author_with_rels):
        author, books = active_author_with_rels
        book_1, book_2 = books
        model = book_2._meta.model
        run_remove_test(
            model.objects.filter(id=book_2.id),
            expected_removed=[book_2],
            expected_active=[author, book_1],
        )


@pytest.mark.django_db
class TestOneToOneCascadeRelation(OneToOneCascadeRelationTestBase):
    def test_remove_called_by_reverse_related(self, active_author):
        model = active_author._meta.model
        run_remove_test(
            model.objects.filter(id=active_author.id),
            expected_removed=[
                active_author,
                active_author.profile,
                active_author.profile.profilemeta,
            ],
        )

    def test_remove_called_by_forward_related(self, active_author):
        model = active_author.profile._meta.model
        run_remove_test(
            model.objects.filter(id=active_author.profile.id),
            expected_removed=[active_author.profile, active_author.profile.profilemeta],
            expected_active=[active_author],
        )

    def test_restore_called_by_reverse_related(self, removed_author):
        model = removed_author._meta.model
        run_restore_test(
            model.objects.filter(id=removed_author.id),
            expected_active=[removed_author],
            expected_removed=[
                removed_author.profile,
                removed_author.profile.profilemeta,
            ],
        )

    def test_restore_with_related_called_by_reverse_related(self, removed_author):
        model = removed_author._meta.model
        run_restore_test(
            model.objects.filter(id=removed_author.id),
            with_related=True,
            expected_active=[
                removed_author,
                removed_author.profile,
                removed_author.profile.profilemeta,
            ],
        )

    def test_restore_called_by_forward_related(self, removed_author):
        model = removed_author.profile._meta.model
        run_restore_test(
            model.objects.filter(id=removed_author.profile.id),
            expected_active=[removed_author, removed_author.profile],
            expected_removed=[removed_author.profile.profilemeta],
        )

    def test_restore_with_related_called_by_forward_related(self, removed_author):
        model = removed_author.profile._meta.model
        run_restore_test(
            model.objects.filter(id=removed_author.profile.id),
            with_related=True,
            expected_active=[
                removed_author,
                removed_author.profile,
                removed_author.profile.profilemeta,
            ],
        )
