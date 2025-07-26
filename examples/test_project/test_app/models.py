from django.db import models

from django_resurrected.models import SoftDeleteModel


class Author(SoftDeleteModel):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name
