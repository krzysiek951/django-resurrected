import pytest
from model_bakery import baker

from examples.test_project.test_app import models


def assert_is_active(*objs):
    for obj in objs:
        obj.refresh_from_db()
        assert obj.is_removed is False
        assert obj.removed_at is None


@pytest.fixture
def make_author():
    return lambda: baker.make(models.Author)


@pytest.fixture
def test_author(make_author):
    author = make_author()
    assert_is_active(author)
    return author
