from django.db import models


class BookFormat(models.TextChoices):
    PAPERBACK = "paperback", "Paperback"
    HARDCOVER = "hardcover", "Hardcover"
    EBOOK = "ebook", "eBook"
