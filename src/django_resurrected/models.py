from __future__ import annotations

from datetime import datetime
from datetime import timedelta

from django.db import models
from django.db import router
from django.utils import timezone
from django.utils.functional import classproperty

from django_resurrected.constants import SOFT_DELETE_RETENTION_DAYS

from .collector import ForwardRelatedCollector
from .collector import ReverseRelatedCollector
from .managers import ActiveObjectsManager
from .managers import AllObjectsManager
from .managers import RemovedObjectsManager
from .utils import restore


class SoftDeleteModel(models.Model):
    retention_days: int | None = SOFT_DELETE_RETENTION_DAYS

    is_removed = models.BooleanField(default=False)
    removed_at = models.DateTimeField(null=True, blank=True)

    objects = AllObjectsManager()
    active_objects = ActiveObjectsManager()
    removed_objects = RemovedObjectsManager()

    class Meta:
        abstract = True

    @classproperty
    def retention_limit(cls) -> datetime | None:
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
            and self.removed_at < self.retention_limit,
        )

    def _get_forward_related_collector(
        self, using: str | None = None
    ) -> ForwardRelatedCollector:
        using = using or router.db_for_write(self.__class__, instance=self)
        return ForwardRelatedCollector(using=using, origin=self)

    def _get_reverse_related_collector(
        self, using: str | None = None
    ) -> ReverseRelatedCollector:
        using = using or router.db_for_write(self.__class__, instance=self)
        return ReverseRelatedCollector(using=using, origin=self)

    def remove(
        self,
        using: str | None = None,
        keep_parents: bool = False,
    ) -> tuple[int, dict[str, int]]:
        collector = self._get_reverse_related_collector(using)
        collector.collect([self], keep_parents=keep_parents)
        return collector.remove()

    def hard_delete(
        self,
        using: str | None = None,
        keep_parents: bool = False,
    ) -> tuple[int, dict[str, int]]:
        return super().delete(using=using, keep_parents=keep_parents)

    def delete(
        self,
        using: str | None = None,
        keep_parents: bool = False,
    ) -> tuple[int, dict[str, int]]:
        if self.is_expired:
            return self.hard_delete(using=using, keep_parents=keep_parents)

        return self.remove(using=using, keep_parents=keep_parents)

    def restore(
        self,
        with_related: bool = False,
        using: str | None = None,
        keep_parents: bool = False,
    ) -> tuple[int, dict[str, int]]:
        forward_rels_collector = self._get_forward_related_collector(using)
        forward_rels_collector.collect([self])
        reverse_rels_collector = self._get_reverse_related_collector(using)
        reverse_rels_collector.collect(
            [self], keep_parents=keep_parents, collect_related=with_related
        )
        return restore(forward_rels_collector, reverse_rels_collector)
