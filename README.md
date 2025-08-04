<div align="center">
  <h1 align="center">django-resurrected</h1>
  <p align="center">
    <strong>Deleted is just a state. Bring your models back.</strong>
  </p>
  <p align="center">
    <a href="https://pypi.org/project/django-resurrected/"><img src="https://img.shields.io/pypi/v/django-resurrected.svg" alt="PyPI Version"></a>
    <a href="https://pypi.org/project/django-resurrected/"><img src="https://img.shields.io/pypi/pyversions/django-resurrected.svg" alt="Python Versions"></a>
  </p>
</div>

---

`django-resurrected` provides soft-delete functionality for Django projects.
Instead of permanently removing objects, it marks them as “removed,” making them easy to restore later.
The package supports **relation-aware deletion** and **restoration**, along with **configurable retention**.

## Table of Contents
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [License](#license)


## Quick Start
### 1. Install

```bash
pip install django-resurrected
```

### 2. Update Your Models

Inherit from `SoftDeleteModel` to enable soft-deletion and restoration:

```python
from django.db import models
from django_resurrected.models import SoftDeleteModel

class Author(SoftDeleteModel):
    name = models.CharField(max_length=100)

class Book(SoftDeleteModel):
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)

class BookMeta(SoftDeleteModel):
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    format = models.CharField(max_length=20)
```

### 3. Use the Enhanced Managers

Each manager now has:
- `.objects` — all records (active + removed)
- `.active_objects` — only active (not removed)
- `.removed_objects` — only soft-deleted

### 4. Remove (Soft-Delete) with Cascading

Removing a parent will also remove its related children:

```python
>>> author = Author.objects.create(name="Frank")
>>> book = Book.objects.create(author=author, title="Dune")
>>> meta = BookMeta.objects.create(book=book, format="ebook")

>>> Author.active_objects.count()
1
>>> Book.active_objects.count()
1
>>> BookMeta.active_objects.count()
1

>>> author.remove()
(3, {'test_app.Author': 1, 'test_app.Book': 1, 'test_app.BookMeta': 1})

>>> Author.active_objects.count()
0
>>> Book.active_objects.count()
0
>>> BookMeta.active_objects.count()
0
```

### 5. Restore: Selective or Cascading

#### Restore only the top-level object

```python
>>> author.restore()
(1, {'test_app.Author': 1})

>>> Author.active_objects.count()
1
>>> Book.active_objects.count()
0
>>> BookMeta.active_objects.count()
0
```

#### Restore with all related objects

```python
>>> author.restore(with_related=True)
(3, {'test_app.Author': 1, 'test_app.Book': 1, 'test_app.BookMeta': 1})

>>> Author.active_objects.count()
1
>>> Book.active_objects.count()
1
>>> BookMeta.active_objects.count()
1
```

#### Restore from a mid-level object

```python
>>> author.remove()
(3, {'test_app.Author': 1, 'test_app.Book': 1, 'test_app.BookMeta': 1})

>>> book.restore()
(2, {'test_app.Book': 1, 'test_app.Author': 1})

>>> Author.active_objects.count()
1
>>> Book.active_objects.count()
1
>>> BookMeta.active_objects.count()
0
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

To permanently remove objects that have exceeded their retention limit, call `purge()`:

```python
>>> TemporaryFile.removed_objects.all().purge()
```

## License

This project is licensed under the MIT License.
