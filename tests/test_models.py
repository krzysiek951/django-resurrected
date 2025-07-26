import pytest
from freezegun import freeze_time


@pytest.mark.django_db
class TestSoftDeleteModel:
    @freeze_time("2025-05-01")
    def test_is_expired(self, test_author):
        assert test_author.retention_days == 30
        assert test_author.is_expired is False
