from __future__ import annotations

from django.db import models

from django_resurrected.collectors import Collector


class BaseQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_removed=False)

    def removed(self):
        return self.filter(is_removed=True)

    def _get_collector(self) -> Collector:
        return Collector(using=self.db, origin=self)

    def hard_delete(self):
        return super().delete()


class ActiveObjectsQuerySet(BaseQuerySet):
    def remove(self):
        collector = self._get_collector()
        collector.collect_reverse_related(self)
        return collector.remove()

    def delete(self):
        return self.remove()


class RemovedObjectsQuerySet(BaseQuerySet):
    def restore(self, with_related: bool = False):
        collector = self._get_collector()
        collector.collect_forward_related(self)
        collector.collect_reverse_related(self, collect_related=with_related)
        return collector.restore()

    def expired(self):
        return self.removed().filter(removed_at__lt=self.model.retention_limit)

    def purge(self):
        return self.expired().hard_delete()  # type: ignore[attr-defined]

    def delete(self):
        return self.purge()


class AllObjectsQuerySet(ActiveObjectsQuerySet, RemovedObjectsQuerySet):
    pass


class AllObjectsManager(models.Manager):
    def get_queryset(self):
        return AllObjectsQuerySet(self.model, using=self._db)


class ActiveObjectsManager(models.Manager):
    def get_queryset(self):
        return ActiveObjectsQuerySet(self.model, using=self._db).active()


class RemovedObjectsManager(models.Manager):
    def get_queryset(self):
        return RemovedObjectsQuerySet(self.model, using=self._db).removed()
