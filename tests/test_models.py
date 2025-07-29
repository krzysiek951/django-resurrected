from datetime import datetime

import pytest
import pytz
from freezegun import freeze_time
from test_app.models import Author

from django_resurrected.managers import ActiveObjectsManager
from django_resurrected.managers import AllObjectsManager
from django_resurrected.managers import RemovedObjectsManager
from tests.conftest import assert_is_active
from tests.conftest import assert_is_removed


@pytest.mark.django_db
class TestSoftDeleteModel:
    def test_manager_type(self, test_author):
        assert isinstance(Author.objects, AllObjectsManager)
        assert isinstance(Author.active_objects, ActiveObjectsManager)
        assert isinstance(Author.removed_objects, RemovedObjectsManager)

    @freeze_time("2025-05-01")
    def test_is_expired(self, test_author, monkeypatch):
        assert_is_active(test_author)
        assert test_author.retention_days == 30
        assert test_author.is_expired is False

        test_author.remove()

        assert_is_removed(test_author)
        assert test_author.is_expired is False

        with freeze_time("2025-05-31"):
            assert test_author.is_expired is False

        with freeze_time("2025-06-01"):
            assert test_author.is_expired

            monkeypatch.setattr(Author, "retention_days", None)
            assert test_author.is_expired is False

    @freeze_time("2025-05-01")
    def test_remove(self, test_author):
        assert_is_active(test_author)

        test_author.remove()

        assert_is_removed(test_author, removed_at=datetime(2025, 5, 1, tzinfo=pytz.utc))

    def test_remove_missing_pk(self):
        author = Author()
        with pytest.raises(
            ValueError,
            match="Operation cannot be performed on Author because its id attribute is "
            "None.",
        ):
            author.remove()

    @freeze_time("2025-05-01")
    def test_remove_with_relation_o2o_cascade(self, author_with_profile):
        author, profile = author_with_profile
        assert_is_active(author, profile)

        author.remove()

        assert_is_removed(
            author, profile, removed_at=datetime(2025, 5, 1, tzinfo=pytz.utc)
        )

    @freeze_time("2025-05-01")
    def test_remove_with_relation_m2o_cascade(self, author_with_books):
        author, books = author_with_books
        book1, book2 = books
        assert_is_active(author, book1, book2)

        author.remove()

        assert_is_removed(
            author, book1, book2, removed_at=datetime(2025, 5, 1, tzinfo=pytz.utc)
        )

    def test_remove_with_relation_m2m(self, book_with_category):
        book, category = book_with_category
        assert_is_active(book, category)

        book.remove()

        assert_is_removed(book)
        # NOTE: M2M relations are not removed, as Django doesn't include them in cascade
        # operations.
        assert_is_active(category)

    def test_hard_delete(self, test_author):
        assert Author.objects.filter(id=test_author.id).exists()
        test_author.hard_delete()
        assert Author.objects.filter(id=test_author.id).exists() is False

    @freeze_time("2025-05-01")
    def test_delete(self, test_author):
        assert_is_active(test_author)

        test_author.delete()

        assert_is_removed(test_author)

        with freeze_time("2025-06-01"):
            test_author.delete()
            assert Author.objects.filter(id=test_author.id).exists() is False

    def test_delete_missing_pk(self):
        author = Author()
        with pytest.raises(
            ValueError,
            match="Operation cannot be performed on Author because its id attribute is "
            "None.",
        ):
            author.delete()

    def test_restore(self, test_author):
        test_author.remove()
        assert_is_removed(test_author)

        test_author.restore()

        assert_is_active(test_author)

    def test_restore_missing_pk(self):
        author = Author()
        with pytest.raises(
            ValueError,
            match="Operation cannot be performed on Author because its id attribute is "
            "None.",
        ):
            author.restore()

    def test_restore_without_related_o2o_cascade(self, author_with_profile):
        author, profile = author_with_profile
        author.remove()
        assert_is_removed(author, profile)

        author.restore(with_related=False)

        assert_is_active(author)
        assert_is_removed(profile)

    def test_restore_with_related_o2o_cascade(self, author_with_profile):
        author, profile = author_with_profile
        author.remove()
        assert_is_removed(author, profile)

        author.restore()

        assert_is_active(author, profile)

    def test_restore_with_related_m2o_cascade(self, author_with_books):
        author, books = author_with_books
        author.remove()
        assert_is_removed(author, *books)

        author.restore()

        assert_is_active(author, *books)

    def test_restore_with_related_m2m(self, book_with_category):
        book, book_category = book_with_category
        book.remove()
        book_category.remove()
        assert_is_removed(book, book_category)

        book.restore()

        assert_is_active(book)
        # NOTE: M2M relations are not restored, as Django doesn't include them in
        # cascade operations.
        assert_is_removed(book_category)

    def test_restore_with_nested_relations(self, author_with_nested_relations):
        author, profile, book, book_meta, category = author_with_nested_relations
        author.remove()
        category.remove()
        assert_is_removed(author, profile, book, book_meta, category)

        author.restore()
        assert_is_active(author, profile, book, book_meta)
        assert_is_removed(category)
