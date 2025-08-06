from __future__ import annotations

import inspect
from collections import Counter
from collections import defaultdict
from collections.abc import Iterable
from collections.abc import Iterator
from typing import TYPE_CHECKING

from django.db import models
from django.db import transaction
from django.db.models import QuerySet
from django.db.models.options import Options
from django.utils import timezone

if TYPE_CHECKING:
    from django_resurrected.models import SoftDeleteModel


def is_soft_delete(obj: models.Model | type[models.Model]) -> bool:
    from .models import SoftDeleteModel  # noqa: PLC0415

    model_class = obj if inspect.isclass(obj) else type(obj)
    return issubclass(model_class, SoftDeleteModel)


def get_candidate_relations_to_restore(opts: Options) -> Iterator[models.Field]:
    return (
        f
        for f in opts.get_fields()
        if not f.auto_created and f.concrete and (f.one_to_one or f.many_to_one)
    )


class Collector(models.deletion.Collector):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model_objs = defaultdict(set)

    def collect(self, objs: Iterable[models.Model], source=None, **kwargs) -> None:
        for obj in objs:
            self.model_objs[obj._meta.model].add(obj)
        return super().collect(objs, **kwargs)

    def can_fast_delete(self, *args, **kwargs) -> bool:
        return False

    def collect_forward_related(
        self, objs: Iterable[models.Model], collect_nullable: bool = False
    ) -> None:
        for obj in objs:
            model = obj._meta.model
            self.model_objs[model].add(obj)

            for field in get_candidate_relations_to_restore(model._meta):
                if not collect_nullable and field.null:
                    continue
                if related_obj := getattr(obj, field.name):
                    self.collect_forward_related([related_obj])

    def collect_reverse_related(self, objs: Iterable[models.Model], **kwargs) -> None:
        return self.collect(objs, **kwargs)

    def get_model_objs_for_update(
        self,
    ) -> Iterator[tuple[type[SoftDeleteModel], set[SoftDeleteModel]]]:
        for model, objs in self.model_objs.items():
            if is_soft_delete(model):
                yield model, objs

    def get_querysets_for_update(self, **filters) -> Iterator[QuerySet]:
        for model, objs in self.get_model_objs_for_update():
            if pk_list := [obj.pk for obj in objs if obj.pk is not None]:
                yield model.objects.filter(pk__in=pk_list, **filters)

    def update(
        self, querysets: Iterable[QuerySet], **kwargs
    ) -> tuple[int, dict[str, int]]:
        counter: Counter[str] = Counter()

        with transaction.atomic(using=self.using):
            for qs in querysets:
                if count := qs.update(**kwargs):
                    counter[qs.model._meta.label] += count

        return sum(counter.values()), dict(counter)

    def restore(self) -> tuple[int, dict[str, int]]:
        querysets = self.get_querysets_for_update(is_removed=True)
        return self.update(querysets, is_removed=False, removed_at=None)

    def remove(self) -> tuple[int, dict[str, int]]:
        querysets = self.get_querysets_for_update(is_removed=False)
        return self.update(querysets, is_removed=True, removed_at=timezone.now())
