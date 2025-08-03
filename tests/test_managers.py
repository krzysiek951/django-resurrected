from datetime import datetime
from unittest.mock import patch

import pytest
import pytz
from freezegun.api import freeze_time
from test_app.models import Author
from test_app.models import AuthorProfile
from test_app.models import Book
from test_app.models import BookCategory
from test_app.models import BookMeta

from django_resurrected.managers import ActiveObjectsQuerySet
from django_resurrected.managers import AllObjectsQuerySet
from django_resurrected.managers import RemovedObjectsQuerySet
from tests.conftest import assert_is_active
from tests.conftest import assert_is_removed
from tests.conftest import remove_objs


@pytest.mark.django_db
class TestActiveObjectsQuerySet:
    @freeze_time("2025-05-01")
    def test_remove(self, make_author):
        authors = make_author(_quantity=3)
        assert_is_active(*authors)

        Author.active_objects.all().remove()

        assert_is_removed(*authors, removed_at=datetime(2025, 5, 1, tzinfo=pytz.utc))

    @freeze_time("2025-05-01")
    def test_remove_with_related_o2o_cascade(self, make_author, make_author_profile):
        author_1, author_2, author_3 = make_author(_quantity=3)
        profile_1 = make_author_profile(author=author_1)
        profile_2 = make_author_profile(author=author_2)
        assert_is_active(author_1, author_2, author_3, profile_1, profile_2)

        Author.active_objects.filter(id=author_1.id).remove()

        assert_is_active(author_2, author_3, profile_2)
        assert_is_removed(
            author_1, profile_1, removed_at=datetime(2025, 5, 1, tzinfo=pytz.utc)
        )

    @freeze_time("2025-05-01")
    def test_remove_with_related_m2o_cascade(self, make_author, make_book):
        author_1, author_2, author_3 = make_author(_quantity=3)
        book_1 = make_book(author=author_1)
        book_2 = make_book(author=author_2)
        assert_is_active(author_1, author_2, author_3, book_1, book_2)

        Author.active_objects.filter(id=author_1.id).remove()

        assert_is_active(author_2, author_3, book_2)
        assert_is_removed(
            author_1, book_1, removed_at=datetime(2025, 5, 1, tzinfo=pytz.utc)
        )

    @freeze_time("2025-05-01")
    def test_remove_with_related_m2m(self, make_author, book_with_category):
        book, category = book_with_category
        author_1 = book.author
        author_2, author_3 = make_author(_quantity=2)
        assert_is_active(author_1, author_2, author_3, book, category)

        Author.active_objects.filter(id=author_1.id).remove()

        assert_is_active(author_2, author_3, category)
        # NOTE: M2M relations are not removed, as Django doesn't include them in cascade
        # operations.
        assert_is_removed(
            author_1, book, removed_at=datetime(2025, 5, 1, tzinfo=pytz.utc)
        )

    @patch.object(ActiveObjectsQuerySet, "remove")
    def test_delete(self, remove_mock):
        Author.active_objects.all().delete()
        remove_mock.assert_called_once()


@pytest.mark.django_db
class TestActiveObjectsQuerySetWithAllRelations:
    def test_remove_author(self, make_author_with_all_relations):
        author_1, author_1_rels = make_author_with_all_relations()
        author_2, author_2_rels = make_author_with_all_relations()
        profile, book_1, book_2, book_meta_1, book_meta_2, category_1, category_2 = (
            author_1_rels
        )
        Author.active_objects.filter(id=author_1.id).remove()

        assert_is_removed(author_1, profile, book_1, book_2, book_meta_1, book_meta_2)
        assert_is_active(category_1, category_2, author_2, *author_2_rels)

    def test_remove_profile(self, make_author_with_all_relations):
        author_1, author_1_rels = make_author_with_all_relations()
        author_2, author_2_rels = make_author_with_all_relations()
        profile, book_1, book_2, book_meta_1, book_meta_2, category_1, category_2 = (
            author_1_rels
        )

        AuthorProfile.active_objects.filter(id=profile.id).remove()

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
        author_3, author_3_rels = make_author_with_all_relations()
        profile, book_1, book_2, book_meta_1, book_meta_2, category_1, category_2 = (
            author_1_rels
        )

        Book.active_objects.filter(id=book_1.id).remove()

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
        author_3, author_3_rels = make_author_with_all_relations()
        profile, book_1, book_2, book_meta_1, book_meta_2, category_1, category_2 = (
            author_1_rels
        )

        BookMeta.active_objects.filter(id=book_meta_1.id).remove()

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

        BookCategory.active_objects.filter(id=category_1.id).remove()

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


@pytest.mark.django_db
class TestRemovedObjectsQuerySet:
    def test_restore(self, make_author):
        author_1, author_2, author_3 = make_author(_quantity=3)
        Author.objects.all().remove()
        assert_is_removed(author_1, author_2, author_3)

        Author.removed_objects.filter(id__in=[author_1.id, author_2.id]).restore()

        assert_is_active(author_1, author_2)
        assert_is_removed(author_3)

    def test_restore_without_related(self, make_author, make_author_profile):
        author_1, author_2, author_3 = make_author(_quantity=3)
        profile_1 = make_author_profile(author=author_1)
        profile_2 = make_author_profile(author=author_2)
        Author.objects.all().remove()
        assert_is_removed(author_1, author_2, author_3, profile_1, profile_2)

        result = Author.removed_objects.filter(id=author_1.id).restore()

        assert_is_active(author_1)
        assert_is_removed(author_2, author_3, profile_1, profile_2)
        assert result == (1, {"test_app.Author": 1})

    def test_restore_with_related_o2o_cascade(self, make_author, make_author_profile):
        author_1, author_2, author_3 = make_author(_quantity=3)
        profile_1 = make_author_profile(author=author_1)
        profile_2 = make_author_profile(author=author_2)
        Author.objects.all().remove()
        assert_is_removed(author_1, author_2, author_3, profile_1, profile_2)

        result = Author.removed_objects.filter(id=author_1.id).restore(
            with_related=True
        )

        assert_is_active(author_1, profile_1)
        assert_is_removed(author_2, author_3, profile_2)
        assert result == (2, {"test_app.Author": 1, "test_app.AuthorProfile": 1})

    def test_restore_with_related_m2o_cascade(self, make_author, make_book):
        author_1, author_2, author_3 = make_author(_quantity=3)
        book_1 = make_book(author=author_1)
        book_2 = make_book(author=author_2)
        Author.active_objects.all().remove()
        assert_is_removed(author_1, author_2, author_3, book_1, book_2)

        Author.removed_objects.filter(id=author_1.id).restore(with_related=True)

        assert_is_active(author_1, book_1)
        assert_is_removed(author_2, author_3, book_2)

    def test_restore_with_related_o2m(self, make_author, make_book):
        author_1, author_2, author_3 = make_author(_quantity=3)
        book_1 = make_book(author=author_1)
        book_2 = make_book(author=author_2)
        Author.active_objects.all().remove()
        assert_is_removed(author_1, author_2, author_3, book_1, book_2)

        Book.removed_objects.filter(id=book_1.id).restore()

        assert_is_active(author_1, book_1)
        assert_is_removed(author_2, author_3, book_2)

    def test_restore_with_related_m2m(self, make_author, book_with_category):
        book, category = book_with_category
        author_1 = book.author
        author_2, author_3 = make_author(_quantity=2)
        Author.active_objects.all().remove()
        category.remove()
        assert_is_removed(author_1, author_2, author_3, book, category)

        Author.removed_objects.filter(id=author_1.id).restore(with_related=True)

        assert_is_active(author_1, book)
        assert_is_removed(author_2, author_3, category)

    @patch.object(RemovedObjectsQuerySet, "purge")
    def test_delete(self, purge_mock, test_author):
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
class TestRemovedObjectsQuerySetWithAllRelations:
    def test_restore_author(self, make_author_with_all_relations):
        author_1, author_1_rels = make_author_with_all_relations()
        author_2, author_2_rels = make_author_with_all_relations()
        remove_objs(author_1, *author_1_rels, author_2, *author_2_rels)

        Author.removed_objects.filter(id=author_1.id).restore()

        assert_is_active(author_1)
        assert_is_removed(*author_1_rels, author_2, *author_2_rels)

    def test_restore_author_with_related(self, make_author_with_all_relations):
        author_1, author_1_rels = make_author_with_all_relations()
        author_2, author_2_rels = make_author_with_all_relations()
        profile, book_1, book_2, book_meta_1, book_meta_2, category_1, category_2 = (
            author_1_rels
        )
        remove_objs(author_1, *author_1_rels, author_2, *author_2_rels)

        Author.removed_objects.filter(id=author_1.id).restore(with_related=True)

        assert_is_active(author_1, profile, book_1, book_2, book_meta_1, book_meta_2)
        assert_is_removed(category_1, category_2, author_2, *author_2_rels)

    def test_restore_profile(self, make_author_with_all_relations):
        author_1, author_1_rels = make_author_with_all_relations()
        author_2, author_2_rels = make_author_with_all_relations()
        profile, book_1, book_2, book_meta_1, book_meta_2, category_1, category_2 = (
            author_1_rels
        )
        remove_objs(author_1, *author_1_rels, author_2, *author_2_rels)

        AuthorProfile.removed_objects.filter(id=profile.id).restore()

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

        AuthorProfile.removed_objects.filter(id=profile.id).restore(with_related=True)

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

        Book.removed_objects.filter(id=book_1.id).restore()

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

        Book.removed_objects.filter(id=book_1.id).restore(with_related=True)

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

        BookMeta.removed_objects.filter(id=book_meta_1.id).restore()

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

        BookMeta.removed_objects.filter(id=book_meta_1.id).restore(with_related=True)

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

        BookCategory.removed_objects.filter(id=category_1.id).restore()

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

        BookCategory.removed_objects.filter(id=category_1.id).restore(with_related=True)

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


@pytest.mark.django_db
class TestAllObjectsQuerySet:
    @patch.object(AllObjectsQuerySet, "remove")
    def test_delete(self, remove_mock):
        Author.objects.all().delete()
        remove_mock.assert_called_once()
