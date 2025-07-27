from datetime import datetime

import pytest
import pytz
from freezegun.api import freeze_time
from test_app.models import Author

from tests.conftest import assert_is_active
from tests.conftest import assert_is_removed


@pytest.mark.django_db
class TestActiveObjectsManager:
    @freeze_time("2025-05-01")
    def test_remove(self, make_authors):
        authors = make_authors()

        Author.active_objects.all().remove()

        assert_is_removed(*authors, removed_at=datetime(2025, 5, 1, tzinfo=pytz.utc))

    @freeze_time("2025-05-01")
    def test_remove_with_related_o2o_cascade(self, make_authors, make_author_profile):
        author_1, author_2, author_3 = make_authors()
        profile_1 = make_author_profile(author=author_1)
        profile_2 = make_author_profile(author=author_2)

        Author.active_objects.filter(id=author_1.id).remove()

        assert_is_active(author_2, author_3, profile_2)
        assert_is_removed(
            author_1, profile_1, removed_at=datetime(2025, 5, 1, tzinfo=pytz.utc)
        )

    @freeze_time("2025-05-01")
    def test_remove_with_related_m2o_cascade(self, make_authors, make_book):
        author_1, author_2, author_3 = make_authors()
        book_1 = make_book(author=author_1)
        book_2 = make_book(author=author_2)

        Author.active_objects.filter(id=author_1.id).remove()

        assert_is_active(author_2, author_3, book_2)
        assert_is_removed(
            author_1, book_1, removed_at=datetime(2025, 5, 1, tzinfo=pytz.utc)
        )

    @freeze_time("2025-05-01")
    def test_remove_with_related_m2m(self, make_authors, book_with_category):
        book, category = book_with_category
        author_1 = book.author
        author_2, author_3 = make_authors(quantity=2)

        Author.active_objects.filter(id=author_1.id).remove()

        assert_is_removed(
            book, author_1, removed_at=datetime(2025, 5, 1, tzinfo=pytz.utc)
        )
        # NOTE: M2M relations are not removed, as Django doesn't include them in cascade
        # operations.
        assert_is_active(author_2, author_3, category)
