from datetime import datetime

import pytest
import pytz
from django.db.models import ProtectedError
from django.db.models import RestrictedError
from freezegun import freeze_time
from test_app.models import Author

from django_resurrected.managers import ActiveObjectsManager
from django_resurrected.managers import AllObjectsManager
from django_resurrected.managers import RemovedObjectsManager
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
class TestSoftDeleteModel:
    def test_manager_type(self, active_author):
        assert isinstance(Author.objects, AllObjectsManager)
        assert isinstance(Author.active_objects, ActiveObjectsManager)
        assert isinstance(Author.removed_objects, RemovedObjectsManager)

    @freeze_time("2025-05-01")
    def test_is_expired(self, active_author, monkeypatch):
        assert_is_active(active_author)
        assert active_author.retention_days == 30
        assert active_author.is_expired is False

        active_author.remove()

        assert_is_removed(active_author)
        assert active_author.is_expired is False

        with freeze_time("2025-05-31"):
            assert active_author.is_expired is False

        with freeze_time("2025-06-01"):
            assert active_author.is_expired

            monkeypatch.setattr(Author, "retention_days", None)
            assert active_author.is_expired is False

    @freeze_time("2025-05-01")
    def test_remove(self, active_author):
        assert_is_active(active_author)
        active_author.remove()
        assert_is_removed(
            active_author, removed_at=datetime(2025, 5, 1, tzinfo=pytz.utc)
        )

    def test_hard_delete(self, active_author):
        assert Author.objects.filter(id=active_author.id).exists()
        active_author.hard_delete()
        assert Author.objects.filter(id=active_author.id).exists() is False

    @freeze_time("2025-05-01")
    def test_delete(self, active_author):
        assert_is_active(active_author)
        active_author.delete()
        assert_is_removed(active_author)
        with freeze_time("2025-06-01"):
            active_author.delete()
            assert Author.objects.filter(id=active_author.id).exists() is False


@pytest.mark.django_db
class TestManyToManyCascadeRelation(ManyToManyCascadeRelationTestBase):
    def test_remove_called_by_reverse_related(self, active_books_with_rels):
        books, book_metas, categories = active_books_with_rels
        cat_1, cat_2, cat_3 = categories
        run_remove_test(
            cat_2,
            expected_removed=[cat_2],
            expected_active=[*books, *book_metas, cat_1, cat_3],
            through_models=["test_app.Book_categories"],
        )

    def test_remove_called_by_forward_related(self, active_books_with_rels):
        books, book_metas, categories = active_books_with_rels
        book_1, book_2, book_3 = books
        run_remove_test(
            book_2,
            expected_removed=[book_2, book_2.bookmeta],
            expected_active=[book_1, book_1.bookmeta, book_3, *categories],
            through_models=["test_app.Book_categories"],
        )

    def test_restore_called_by_reverse_related(self, removed_books_with_rels):
        books, book_metas, categories = removed_books_with_rels
        cat_1, cat_2, cat_3 = categories
        run_restore_test(
            cat_2,
            expected_active=[cat_2],
            expected_removed=[*books, *book_metas, cat_1, cat_3],
        )

    def test_restore_with_related_called_by_reverse_related(
        self, removed_books_with_rels
    ):
        books, book_metas, categories = removed_books_with_rels
        cat_1, cat_2, cat_3 = categories
        run_restore_test(
            cat_2,
            with_related=True,
            expected_active=[cat_2],
            expected_removed=[*books, *book_metas, cat_1, cat_3],
        )

    def test_restore_called_by_forward_related(self, removed_books_with_rels):
        books, book_metas, categories = removed_books_with_rels
        book_1, book_2, book_3 = books
        run_restore_test(
            book_2,
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
        run_restore_test(
            book_2,
            with_related=True,
            expected_active=[book_2, book_2.bookmeta],
            expected_removed=[book_1, book_1.bookmeta, book_3, *categories],
        )


@pytest.mark.django_db
class TestManyToOneCascadeRelation(ManyToOneCascadeRelationTestBase):
    def test_remove_called_by_reverse_related(self, active_author_with_rels):
        author, books, book_metas = active_author_with_rels
        run_remove_test(
            author,
            expected_removed=[author, *books, *book_metas],
        )

    def test_remove_called_by_forward_related(self, active_author_with_rels):
        author, books, book_metas = active_author_with_rels
        book_1, book_2, book_3 = books
        run_remove_test(
            book_2,
            expected_removed=[book_2, book_2.bookmeta],
            expected_active=[author, book_1, book_1.bookmeta, book_3],
        )

    def test_restore_called_by_reverse_related(self, removed_author_with_rels):
        author, books, book_metas = removed_author_with_rels
        run_restore_test(
            author,
            expected_active=[author],
            expected_removed=[*books, *book_metas],
        )

    def test_restore_with_related_called_by_reverse_related(
        self, removed_author_with_rels
    ):
        author, books, book_metas = removed_author_with_rels
        run_restore_test(
            author,
            with_related=True,
            expected_active=[author, *books, *book_metas],
        )

    def test_restore_called_by_forward_related(self, removed_author_with_rels):
        author, books, book_metas = removed_author_with_rels
        book_1, book_2, book_3 = books
        run_restore_test(
            book_2,
            expected_active=[author, book_2],
            expected_removed=[book_1, book_1.bookmeta, book_2.bookmeta, book_3],
        )

    def test_restore_with_related_called_by_forward_related(
        self, removed_author_with_rels
    ):
        author, books, book_metas = removed_author_with_rels
        book_1, book_2, book_3 = books
        run_restore_test(
            book_2,
            with_related=True,
            expected_active=[author, book_2, book_2.bookmeta],
            expected_removed=[book_1, book_1.bookmeta, book_3],
        )


@pytest.mark.django_db
class TestManyToOneProtectRelation(ManyToOneProtectRelationTestBase):
    def test_remove_called_by_reverse_related(self, active_author_with_rels):
        author, _ = active_author_with_rels
        with pytest.raises(ProtectedError):
            author.remove()

    def test_test_remove_called_by_forward_related(self, active_author_with_rels):
        author, books = active_author_with_rels
        book_1, book_2 = books
        run_remove_test(
            book_2,
            expected_removed=[book_2],
            expected_active=[author, book_1],
        )


@pytest.mark.django_db
class TestManyToOneRestrictRelation(ManyToOneRestrictRelationTestBase):
    @pytest.fixture
    def active_author_with_rels(self, make_author, make_book_restrict):
        author = make_author()
        book_1, book_2 = make_book_restrict(author=author, _quantity=2)
        assert_is_active(author, book_1, book_2)
        return author, (book_1, book_2)

    def test_remove_called_by_reverse_related(self, active_author_with_rels):
        author, books = active_author_with_rels
        with pytest.raises(RestrictedError):
            author.remove()

    def test_test_remove_called_by_forward_related(self, active_author_with_rels):
        author, books = active_author_with_rels
        book_1, book_2 = books
        run_remove_test(
            book_2,
            expected_removed=[book_2],
            expected_active=[author, book_1],
        )


@pytest.mark.django_db
class TestOneToOneCascadeRelation(OneToOneCascadeRelationTestBase):
    def test_remove_called_by_reverse_related(self, active_author):
        run_remove_test(
            active_author,
            expected_removed=[
                active_author,
                active_author.profile,
                active_author.profile.profilemeta,
            ],
        )

    def test_remove_called_by_forward_related(self, active_author):
        run_remove_test(
            active_author.profile,
            expected_removed=[active_author.profile, active_author.profile.profilemeta],
            expected_active=[active_author],
        )

    def test_restore_called_by_reverse_related(self, removed_author):
        run_restore_test(
            removed_author,
            expected_active=[removed_author],
            expected_removed=[
                removed_author.profile,
                removed_author.profile.profilemeta,
            ],
        )

    def test_restore_with_related_called_by_reverse_related(self, removed_author):
        run_restore_test(
            removed_author,
            with_related=True,
            expected_active=[
                removed_author,
                removed_author.profile,
                removed_author.profile.profilemeta,
            ],
        )

    def test_restore_called_by_forward_related(self, removed_author):
        run_restore_test(
            removed_author.profile,
            expected_active=[removed_author, removed_author.profile],
            expected_removed=[removed_author.profile.profilemeta],
        )

    def test_restore_with_related_called_by_forward_related(self, removed_author):
        run_restore_test(
            removed_author.profile,
            with_related=True,
            expected_active=[
                removed_author,
                removed_author.profile,
                removed_author.profile.profilemeta,
            ],
        )
