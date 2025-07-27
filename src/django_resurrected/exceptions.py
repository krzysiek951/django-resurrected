class SoftDeleteException(Exception):
    pass


class MissingPrimaryKeyException(SoftDeleteException, ValueError):
    def __init__(self, obj_name: str, pk_attname: str):
        self.object_name = obj_name
        self.pk_attname = pk_attname

    def __str__(self):
        return (
            f"Operation cannot be performed on {self.object_name} because its "
            f"{self.pk_attname} attribute is None."
        )
