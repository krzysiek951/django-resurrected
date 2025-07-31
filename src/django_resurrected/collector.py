from __future__ import annotations

import inspect
from collections import Counter
from typing import TYPE_CHECKING

from django.contrib.admin.utils import NestedObjects
from django.db import models
from django.utils import timezone

if TYPE_CHECKING:
    from django_resurrected.managers import AllObjectsQuerySet
    from django_resurrected.models import SoftDeleteModel


def is_soft_delete(obj: models.Model | type[models.Model]) -> bool:
    from .models import SoftDeleteModel  # noqa: PLC0415

    model_class = obj if inspect.isclass(obj) else type(obj)
    return issubclass(model_class, SoftDeleteModel)


class SoftDeleteCollector(NestedObjects):
    @property
    def model_objs_for_soft_delete(
        self,
    ) -> dict[type[SoftDeleteModel], set[SoftDeleteModel]]:
        return {
            model: objs
            for model, objs in self.model_objs.items()
            if is_soft_delete(model)
        }

    @property
    def querysets_for_soft_delete(self) -> list[AllObjectsQuerySet]:
        querysets = []

        for model, objs in self.model_objs_for_soft_delete.items():
            if pk_list := [obj.pk for obj in objs if obj.pk is not None]:
                querysets.append(model.objects.filter(pk__in=pk_list))

        return querysets

    def update(self, **kwargs) -> tuple[int, dict[str, int]]:
        counter: Counter[str] = Counter()

        for queryset in self.querysets_for_soft_delete:
            count = queryset.update(**kwargs)
            counter[queryset.model._meta.label] += count

        return sum(counter.values()), dict(counter)

    def remove(self) -> tuple[int, dict[str, int]]:
        return self.update(is_removed=True, removed_at=timezone.now())

    def restore(self) -> tuple[int, dict[str, int]]:
        return self.update(is_removed=False, removed_at=None)
