from django.db import models

from django_resurrected.models import SoftDeleteModel

from .constants import BookFormat


class Author(SoftDeleteModel):
    name = models.CharField(max_length=100)


class AuthorProfile(SoftDeleteModel):
    author = models.OneToOneField(
        Author, on_delete=models.CASCADE, related_name="profile"
    )
    bio = models.TextField(blank=True)


class BookCategory(SoftDeleteModel):
    name = models.CharField(max_length=100, unique=True)


class Book(SoftDeleteModel):
    title = models.CharField(max_length=100)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    categories = models.ManyToManyField(BookCategory, related_name="books", blank=True)


class BookMeta(SoftDeleteModel):
    book = models.OneToOneField(Book, on_delete=models.CASCADE, related_name="meta")
    format = models.CharField(
        max_length=30, choices=BookFormat.choices, default=BookFormat.PAPERBACK
    )
