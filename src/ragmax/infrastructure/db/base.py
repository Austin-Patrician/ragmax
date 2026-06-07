from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def import_models() -> None:
    from ragmax.infrastructure.db import models  # noqa: F401
