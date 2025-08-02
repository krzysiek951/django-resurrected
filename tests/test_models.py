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
from tests.conftest import remove_objs


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

        result = author.restore()

        assert_is_active(author)
        assert_is_removed(profile)
        assert result == (1, {"test_app.Author": 1})

    def test_restore_with_related_o2o_cascade(self, author_with_profile):
        author, profile = author_with_profile
        author.remove()
        assert_is_removed(author, profile)

        result = author.restore(with_related=True)

        assert_is_active(author, profile)
        assert result == (2, {"test_app.Author": 1, "test_app.AuthorProfile": 1})

    def test_restore_with_related_m2o_cascade(self, author_with_books):
        author, books = author_with_books
        author.remove()
        assert_is_removed(author, *books)

        author.restore(with_related=True)

        assert_is_active(author, *books)

    def test_restore_with_related_o2m(self, author_with_books):
        author, books = author_with_books
        book_1, book_2 = books
        author.remove()
        assert_is_removed(author, book_1, book_2)

        book_1.restore(with_related=True)

        assert_is_active(author, book_1)
        assert_is_removed(book_2)

    def test_restore_with_related_m2m(self, book_with_category):
        book, book_category = book_with_category
        book.remove()
        book_category.remove()
        assert_is_removed(book, book_category)

        book.restore(with_related=True)

        assert_is_active(book)
        # NOTE: M2M relations are not restored, as Django doesn't include them in
        # cascade operations.
        assert_is_removed(book_category)


@pytest.mark.django_db
class TestSoftDeleteModelWithAllRelations:
    def test_remove_author(self, make_author_with_all_relations):
        author_1, author_1_rels = make_author_with_all_relations()
        author_2, author_2_rels = make_author_with_all_relations()
        profile, book_1, book_2, book_meta_1, book_meta_2, category_1, category_2 = (
            author_1_rels
        )
        author_1.remove()

        assert_is_removed(author_1, profile, book_1, book_2, book_meta_1, book_meta_2)
        assert_is_active(category_1, category_2, author_2, *author_2_rels)

    def test_remove_profile(self, make_author_with_all_relations):
        author_1, author_1_rels = make_author_with_all_relations()
        author_2, author_2_rels = make_author_with_all_relations()
        profile, book_1, book_2, book_meta_1, book_meta_2, category_1, category_2 = (
            author_1_rels
        )

        profile.remove()

        assert_is_removed(profile)
        assert_is_active(
            author_1,
            book_1,
            book_2,
            book_meta_1,
            book_meta_2,
            category_1,
            category_2,
            author_2,
            *author_2_rels,
        )

    def test_remove_book(self, make_author_with_all_relations):
        author_1, author_1_rels = make_author_with_all_relations()
        author_2, author_2_rels = make_author_with_all_relations()
        profile, book_1, book_2, book_meta_1, book_meta_2, category_1, category_2 = (
            author_1_rels
        )

        book_1.remove()

        assert_is_removed(book_1, book_meta_1)
        assert_is_active(
            profile,
            book_2,
            book_meta_2,
            category_1,
            category_2,
            author_2,
            *author_2_rels,
        )

    def test_remove_book_meta(self, make_author_with_all_relations):
        author_1, author_1_rels = make_author_with_all_relations()
        author_2, author_2_rels = make_author_with_all_relations()
        profile, book_1, book_2, book_meta_1, book_meta_2, category_1, category_2 = (
            author_1_rels
        )

        book_meta_1.remove()

        assert_is_removed(book_meta_1)
        assert_is_active(
            author_1,
            book_1,
            profile,
            book_2,
            book_meta_2,
            category_1,
            category_2,
            author_2,
            *author_2_rels,
        )

    def test_remove_category(self, make_author_with_all_relations):
        author_1, author_1_rels = make_author_with_all_relations()
        author_2, author_2_rels = make_author_with_all_relations()
        profile, book_1, book_2, book_meta_1, book_meta_2, category_1, category_2 = (
            author_1_rels
        )

        category_1.remove()

        assert_is_removed(category_1)
        assert_is_active(
            author_1,
            profile,
            book_1,
            book_2,
            book_meta_1,
            book_meta_2,
            category_2,
            author_2,
            *author_2_rels,
        )

    def test_restore_author(self, make_author_with_all_relations):
        author_1, author_1_rels = make_author_with_all_relations()
        author_2, author_2_rels = make_author_with_all_relations()
        remove_objs(author_1, *author_1_rels, author_2, *author_2_rels)

        author_1.restore()

        assert_is_active(author_1)
        assert_is_removed(*author_1_rels, author_2, *author_2_rels)

    def test_restore_author_with_related(self, make_author_with_all_relations):
        author_1, author_1_rels = make_author_with_all_relations()
        author_2, author_2_rels = make_author_with_all_relations()
        profile, book_1, book_2, book_meta_1, book_meta_2, category_1, category_2 = (
            author_1_rels
        )
        remove_objs(author_1, *author_1_rels, author_2, *author_2_rels)

        author_1.restore(with_related=True)

        assert_is_active(author_1, profile, book_1, book_2, book_meta_1, book_meta_2)
        assert_is_removed(category_1, category_2, author_2, *author_2_rels)

    def test_restore_profile(self, make_author_with_all_relations):
        author_1, author_1_rels = make_author_with_all_relations()
        author_2, author_2_rels = make_author_with_all_relations()
        profile, book_1, book_2, book_meta_1, book_meta_2, category_1, category_2 = (
            author_1_rels
        )
        remove_objs(author_1, *author_1_rels, author_2, *author_2_rels)

        profile.restore()

        assert_is_active(author_1, profile)
        assert_is_removed(
            book_1,
            book_2,
            book_meta_1,
            book_meta_2,
            category_1,
            category_2,
            author_2,
            *author_2_rels,
        )

    def test_restore_profile_with_related(self, make_author_with_all_relations):
        author_1, author_1_rels = make_author_with_all_relations()
        author_2, author_2_rels = make_author_with_all_relations()
        profile, book_1, book_2, book_meta_1, book_meta_2, category_1, category_2 = (
            author_1_rels
        )
        remove_objs(author_1, *author_1_rels, author_2, *author_2_rels)

        profile.restore(with_related=True)

        assert_is_active(author_1, profile)
        assert_is_removed(
            book_1,
            book_2,
            book_meta_1,
            book_meta_2,
            category_1,
            category_2,
            author_2,
            *author_2_rels,
        )

    def test_restore_book(self, make_author_with_all_relations):
        author_1, author_1_rels = make_author_with_all_relations()
        author_2, author_2_rels = make_author_with_all_relations()
        profile, book_1, book_2, book_meta_1, book_meta_2, category_1, category_2 = (
            author_1_rels
        )
        remove_objs(author_1, *author_1_rels, author_2, *author_2_rels)

        book_1.restore()

        assert_is_active(author_1, book_1)
        assert_is_removed(
            profile,
            book_2,
            book_meta_1,
            book_meta_2,
            category_1,
            category_2,
            author_2,
            *author_2_rels,
        )

    def test_restore_book_with_related(self, make_author_with_all_relations):
        author_1, author_1_rels = make_author_with_all_relations()
        author_2, author_2_rels = make_author_with_all_relations()
        profile, book_1, book_2, book_meta_1, book_meta_2, category_1, category_2 = (
            author_1_rels
        )
        remove_objs(author_1, *author_1_rels, author_2, *author_2_rels)

        book_1.restore(with_related=True)

        assert_is_active(author_1, book_1, book_meta_1)
        assert_is_removed(
            profile,
            book_2,
            book_meta_2,
            category_1,
            category_2,
            author_2,
            *author_2_rels,
        )

    def test_restore_book_meta(self, make_author_with_all_relations):
        author_1, author_1_rels = make_author_with_all_relations()
        author_2, author_2_rels = make_author_with_all_relations()
        profile, book_1, book_2, book_meta_1, book_meta_2, category_1, category_2 = (
            author_1_rels
        )
        remove_objs(author_1, *author_1_rels, author_2, *author_2_rels)

        book_meta_1.restore()

        assert_is_active(author_1, book_1, book_meta_1)
        assert_is_removed(
            profile,
            book_2,
            book_meta_2,
            category_1,
            category_2,
            author_2,
            *author_2_rels,
        )

    def test_restore_book_meta_with_related(self, make_author_with_all_relations):
        author_1, author_1_rels = make_author_with_all_relations()
        author_2, author_2_rels = make_author_with_all_relations()
        profile, book_1, book_2, book_meta_1, book_meta_2, category_1, category_2 = (
            author_1_rels
        )
        remove_objs(author_1, *author_1_rels, author_2, *author_2_rels)

        book_meta_1.restore(with_related=True)

        assert_is_active(author_1, book_1, book_meta_1)
        assert_is_removed(
            profile,
            book_2,
            book_meta_2,
            category_1,
            category_2,
            author_2,
            *author_2_rels,
        )

    def test_restore_category(self, make_author_with_all_relations):
        author_1, author_1_rels = make_author_with_all_relations()
        author_2, author_2_rels = make_author_with_all_relations()
        profile, book_1, book_2, book_meta_1, book_meta_2, category_1, category_2 = (
            author_1_rels
        )
        remove_objs(author_1, *author_1_rels, author_2, *author_2_rels)

        category_1.restore()

        assert_is_active(category_1)
        assert_is_removed(
            author_1,
            profile,
            book_1,
            book_2,
            book_meta_1,
            book_meta_2,
            category_2,
            author_2,
            *author_2_rels,
        )

    def test_restore_category_with_related(self, make_author_with_all_relations):
        author_1, author_1_rels = make_author_with_all_relations()
        author_2, author_2_rels = make_author_with_all_relations()
        profile, book_1, book_2, book_meta_1, book_meta_2, category_1, category_2 = (
            author_1_rels
        )
        remove_objs(author_1, *author_1_rels, author_2, *author_2_rels)

        category_1.restore(with_related=True)

        assert_is_active(category_1)
        assert_is_removed(
            author_1,
            profile,
            book_1,
            book_2,
            book_meta_1,
            book_meta_2,
            category_2,
            author_2,
            *author_2_rels,
        )
