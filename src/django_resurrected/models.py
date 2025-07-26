from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from django.db import models
from django.utils import timezone
from django.utils.functional import classproperty

from django_resurrected.constants import SOFT_DELETE_RETENTION_DAYS


class SoftDeleteModel(models.Model):
    retention_days: Optional[int] = SOFT_DELETE_RETENTION_DAYS

    is_removed = models.BooleanField(default=False)
    removed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    @classproperty
    def retention_limit(cls) -> Optional[datetime]:
        if cls.retention_days is None:
            return None

        return timezone.now() - timedelta(days=cls.retention_days)

    @property
    def is_expired(self) -> bool:
        if self.retention_limit is None:
            return False

        return bool(
            self.is_removed
            and self.removed_at
            and self.removed_at < self.retention_limit
        )
