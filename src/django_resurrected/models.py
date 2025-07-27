from __future__ import annotations

from datetime import datetime
from datetime import timedelta

from django.db import models
from django.db import router
from django.utils import timezone
from django.utils.functional import classproperty

from django_resurrected.constants import SOFT_DELETE_RETENTION_DAYS
from django_resurrected.utils import get_restore_params
from django_resurrected.utils import update_obj

from .collector import SoftDeleteCollector
from .exceptions import MissingPrimaryKeyException
from .managers import ActiveObjectsManager
from .managers import AllObjectsManager
from .managers import RemovedObjectsManager


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

    def _ensure_pk(self) -> None:
        if self.pk is None:
            raise MissingPrimaryKeyException(
                self._meta.object_name, self._meta.pk.attname
            )

    def _get_collector(self, using: str | None = None) -> SoftDeleteCollector:
        using = using or router.db_for_write(self.__class__, instance=self)
        return SoftDeleteCollector(using=using, origin=self)

    def _collect_related(
        self,
        using: str | None = None,
        keep_parents: bool = False,
    ) -> SoftDeleteCollector:
        collector = self._get_collector(using)
        collector.collect([self], keep_parents=keep_parents)
        return collector

    def remove(
        self,
        using: str | None = None,
        keep_parents: bool = False,
    ) -> tuple[int, dict[str, int]]:
        self._ensure_pk()
        collector = self._collect_related(using=using, keep_parents=keep_parents)
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
        self._ensure_pk()
        if self.is_expired:
            return self.hard_delete(using=using, keep_parents=keep_parents)

        return self.remove(using=using, keep_parents=keep_parents)

    def restore(
        self,
        with_related: bool = True,
        using: str | None = None,
        keep_parents: bool = False,
    ) -> tuple[int, dict[str, int]]:
        self._ensure_pk()
        if with_related:
            collector = self._collect_related(using=using, keep_parents=keep_parents)
            return collector.restore()

        update_obj(self, **get_restore_params())
        return 1, {self._meta.label: 1}
