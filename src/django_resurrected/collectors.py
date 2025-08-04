from __future__ import annotations

import inspect
from collections import Counter
from collections.abc import Iterable
from collections.abc import Iterator
from typing import TYPE_CHECKING

from django.contrib.admin.utils import NestedObjects
from django.db import models
from django.db.models.options import Options
from django.utils import timezone

if TYPE_CHECKING:
    from django_resurrected.managers import AllObjectsQuerySet
    from django_resurrected.models import SoftDeleteModel


def is_soft_delete(obj: models.Model | type[models.Model]) -> bool:
    from .models import SoftDeleteModel  # noqa: PLC0415

    model_class = obj if inspect.isclass(obj) else type(obj)
    return issubclass(model_class, SoftDeleteModel)


def get_candidate_relations_to_restore(opts: Options) -> Iterator[models.Field]:
    return (
        f
        for f in opts.get_fields(include_hidden=True)
        if not f.auto_created and f.concrete and (f.one_to_one or f.many_to_one)
    )


class Collector(NestedObjects):
    def collect_forward_related(self, objs: Iterable[models.Model]) -> None:
        for obj in objs:
            model = obj.__class__
            self.model_objs[model].add(obj)

            for field in get_candidate_relations_to_restore(model._meta):
                if field.null:
                    continue
                if related_obj := getattr(obj, field.name):
                    self.collect_forward_related([related_obj])

    def collect_reverse_related(self, objs: Iterable[models.Model], **kwargs) -> None:
        return self.collect(objs, **kwargs)

    @property
    def model_objs_for_update(
        self,
    ) -> dict[type[SoftDeleteModel], set[SoftDeleteModel]]:
        return {
            model: objs
            for model, objs in self.model_objs.items()
            if is_soft_delete(model)
        }

    @property
    def querysets_for_update(self) -> list[AllObjectsQuerySet]:
        querysets = []

        for model, objs in self.model_objs_for_update.items():
            if pk_list := [obj.pk for obj in objs if obj.pk is not None]:
                querysets.append(model.objects.filter(pk__in=pk_list))

        return querysets

    def update(self, **kwargs) -> tuple[int, dict[str, int]]:
        counter: Counter[str] = Counter()

        for queryset in self.querysets_for_update:
            count = queryset.update(**kwargs)
            counter[queryset.model._meta.label] += count

        return sum(counter.values()), dict(counter)

    def restore(self) -> tuple[int, dict[str, int]]:
        return self.update(is_removed=False, removed_at=None)

    def remove(self) -> tuple[int, dict[str, int]]:
        return self.update(is_removed=True, removed_at=timezone.now())
