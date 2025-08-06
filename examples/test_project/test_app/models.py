import uuid

from django.db import models

from django_resurrected.models import SoftDeleteModel


class BaseModel(SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class Author(BaseModel):
    pass


class AuthorProfile(BaseModel):
    author = models.OneToOneField(
        Author, on_delete=models.CASCADE, related_name="profile"
    )


class BookCategory(BaseModel):
    pass


class Book(BaseModel):
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name="books")
    categories = models.ManyToManyField(BookCategory, related_name="books", blank=True)


class BookProtect(BaseModel):
    author = models.ForeignKey(
        Author, on_delete=models.PROTECT, related_name="books_protected"
    )


class BookRestrict(BaseModel):
    author = models.ForeignKey(
        Author, on_delete=models.RESTRICT, related_name="books_restricted"
    )


class BookNullable(BaseModel):
    author = models.ForeignKey(
        Author, on_delete=models.SET_NULL, related_name="books_nullable", null=True
    )


class BookMeta(BaseModel):
    book = models.OneToOneField(Book, on_delete=models.CASCADE, related_name="meta")
