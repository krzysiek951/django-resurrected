from __future__ import annotations

import inspect

from django.db import models
from django.utils import timezone


def is_soft_delete(obj: models.Model | type[models.Model]) -> bool:
    from .models import SoftDeleteModel  # noqa: PLC0415

    model_class = obj if inspect.isclass(obj) else type(obj)
    return issubclass(model_class, SoftDeleteModel)


def update_obj(obj: models.Model, **kwargs) -> None:
    for field, value in kwargs.items():
        setattr(obj, field, value)
    obj.save(update_fields=kwargs.keys())


def get_remove_params() -> dict:
    return {"is_removed": True, "removed_at": timezone.now()}


def get_restore_params() -> dict:
    return {"is_removed": False, "removed_at": None}
