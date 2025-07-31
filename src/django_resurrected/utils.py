from __future__ import annotations

from django_resurrected.collector import ForwardRelatedCollector
from django_resurrected.collector import ReverseRelatedCollector


def restore(
    *collectors: ReverseRelatedCollector | ForwardRelatedCollector,
) -> tuple[int, dict[str, int]]:
    total_restored = 0
    total_restored_per_model = {}

    for collector in collectors:
        num_restored, num_restored_per_model = collector.restore()
        total_restored += num_restored
        total_restored_per_model.update(num_restored_per_model)

    # Subtract 1 to avoid counting root object twice.
    return total_restored - 1, total_restored_per_model
