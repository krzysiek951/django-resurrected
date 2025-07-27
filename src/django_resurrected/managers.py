from __future__ import annotations

from django.db import models

from .collector import SoftDeleteCollector
from .utils import get_restore_params


class BaseQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_removed=False)

    def removed(self):
        return self.filter(is_removed=True)

    def _get_collector(self):
        return SoftDeleteCollector(using=self.db, origin=self)

    def _collect_related(self):
        collector = self._get_collector()
        collector.collect(self)
        return collector

    def hard_delete(self):
        return super().delete()


class ActiveObjectsQuerySet(BaseQuerySet):
    def remove(self):
        collector = self._collect_related()
        return collector.remove()

    def delete(self):
        return self.remove()


class RemovedObjectsQuerySet(BaseQuerySet):
    def restore(self, with_related: bool = True):
        if with_related:
            collector = self._collect_related()
            return collector.restore()
        return self.update(**get_restore_params())

    def expired(self):
        return self.removed().filter(removed_at__lt=self.model.retention_limit)

    def purge(self):
        return self.expired().hard_delete()  # type: ignore[attr-defined]

    def delete(self):
        return self.purge()


class AllObjectsQuerySet(ActiveObjectsQuerySet, RemovedObjectsQuerySet):
    def delete(self):
        return self.remove()


class AllObjectsManager(models.Manager):
    def get_queryset(self):
        return AllObjectsQuerySet(self.model, using=self._db)


class ActiveObjectsManager(models.Manager):
    def get_queryset(self):
        return ActiveObjectsQuerySet(self.model, using=self._db).active()


class RemovedObjectsManager(models.Manager):
    def get_queryset(self):
        return RemovedObjectsQuerySet(self.model, using=self._db).removed()
