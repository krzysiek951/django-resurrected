<div align="center">
  <h1 align="center">django-resurrected</h1>
  <p align="center">
    <strong>Deleted is just a state. Bring your models back.</strong>
  </p>
  <p align="center">
    <a href="https://pypi.org/project/django-resurrected/"><img src="https://img.shields.io/pypi/v/django-resurrected.svg" alt="PyPI Version"></a>
    <a href="https://github.com/krzysiek951/django-resurrected/actions"><img src="https://img.shields.io/github/actions/workflow/status/krzysiek951/django-resurrected/main.yml?branch=main" alt="Build Status"></a>
    <a href="https://codecov.io/gh/krzysiek951/django-resurrected"><img src="https://img.shields.io/codecov/c/github/krzysiek951/django-resurrected.svg" alt="Coverage Status"></a>
    <a href="https://pypi.org/project/django-resurrected/"><img src="https://img.shields.io/pypi/pyversions/django-resurrected.svg" alt="Python Versions"></a>
  </p>
</div>

---

`django-resurrected` provides robust soft-deletion capabilities for your Django projects. Instead of permanently deleting objects from your database, this package marks them as "removed," allowing you to restore them later. This is an invaluable safety net against accidental data loss.

## Why `django-resurrected`?

-   **Prevent Data Loss**: Protect your application's data from accidental deletion by users or developers.
-   **Maintain Data Integrity**: Cascading soft-deletes ensure that related objects are handled correctly, preserving relationships.
-   **Full Control**: Flexible model managers give you granular control over querying active, removed, or all objects.
-   **Easy Integration**: Simply inherit from `SoftDeleteModel` to add soft-deletion capabilities to any model.

## Table of Contents

-   [Features](#features)
-   [Installation](#installation)
-   [Quick Start](#quick-start)
-   [Usage Guide](#usage-guide)
    -   [Model Managers](#model-managers)
    -   [Deleting and Restoring](#deleting-and-restoring)
    -   [Permanent Deletion (Purging)](#permanent-deletion-purging)
-   [Configuration](#configuration)
-   [License](#license)

## Features

-   ✅ **Effortless Soft Deletion**: "Delete" objects without permanently losing them.
-   ✅ **Simple Restoration**: Restore soft-deleted objects with a single command.
-   ✅ **Cascading Deletes**: Automatically soft-delete related objects.
-   ✅ **Configurable Retention Periods**: Control how long to keep removed objects before they can be purged.
-   ✅ **Full Typing Support**: Enjoy a modern development experience with complete type hints.

## Installation

Install the package from PyPI:

```bash
pip install django-resurrected
```

## Quick Start

1.  **Inherit from `SoftDeleteModel`**: Update your model to inherit from `django_resurrected.models.SoftDeleteModel`.
2.  **Use the New Managers**: Your model will now have `objects`, `active_objects`, and `removed_objects` managers.

Here’s a quick example:

```python
# your_app/models.py
from django.db import models
from django_resurrected.models import SoftDeleteModel

class BlogPost(SoftDeleteModel):
    title = models.CharField(max_length=200)
    content = models.TextField()

    def __str__(self):
        return self.title
```

Now you can manage your model instances safely:

```python
>>> # Create a new post
>>> post = BlogPost.objects.create(title="My First Post")
>>> BlogPost.active_objects.count()
1

>>> # Soft-delete the post
>>> post.remove()
>>> BlogPost.active_objects.count()
0
>>> BlogPost.removed_objects.count()
1

>>> # Restore the post
>>> post.restore()
>>> BlogPost.active_objects.count()
1
```

## Usage Guide

### Model Managers

`SoftDeleteModel` equips your model with three distinct managers:

-   `YourModel.objects`: The default manager. Returns **all** objects (both active and removed).
-   `YourModel.active_objects`: Returns only active (not deleted) objects. Use this for most of your application logic.
-   `YourModel.removed_objects`: Returns only soft-deleted objects.

### Deleting and Restoring

You can perform soft-delete and restore operations on both individual instances and querysets.

-   `instance.remove()`: Soft-deletes a single model instance and its related objects.
-   `instance.restore()`: Restores a soft-deleted instance and its related objects.
-   `queryset.remove()`: Soft-deletes all objects in a queryset.
-   `queryset.restore()`: Restores all objects in a queryset.

### Permanent Deletion (Purging)

You can permanently delete objects that have passed their retention period. By default, objects are retained for 30 days.

```python
# Check if an object is expired and ready for purging
>>> post.is_expired
False

# Purge all expired objects for a model
>>> BlogPost.removed_objects.expired().purge()
```

## Configuration

You can customize the retention period by setting the `retention_days` attribute on your model. Set it to `None` to keep objects indefinitely.

```python
# your_app/models.py
from django_resurrected.models import SoftDeleteModel

class ImportantDocument(SoftDeleteModel):
    # Keep forever
    retention_days = None
    content = models.TextField()

class TemporaryFile(SoftDeleteModel):
    # Keep for one week
    retention_days = 7
    data = models.BinaryField()
```

## License

This project is licensed under the MIT License.