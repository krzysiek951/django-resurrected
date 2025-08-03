import uuid

from django.db import models

from django_resurrected.models import SoftDeleteModel

from .constants import BookFormat


class BaseModel(SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class Author(BaseModel):
    name = models.CharField(max_length=100)


class AuthorProfile(BaseModel):
    author = models.OneToOneField(
        Author, on_delete=models.CASCADE, related_name="profile"
    )
    bio = models.TextField(blank=True)


class BookCategory(BaseModel):
    name = models.CharField(max_length=100, unique=True)


class Book(BaseModel):
    title = models.CharField(max_length=100)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    categories = models.ManyToManyField(BookCategory, related_name="books", blank=True)


class BookMeta(BaseModel):
    book = models.OneToOneField(Book, on_delete=models.CASCADE, related_name="meta")
    format = models.CharField(
        max_length=30, choices=BookFormat.choices, default=BookFormat.PAPERBACK
    )
