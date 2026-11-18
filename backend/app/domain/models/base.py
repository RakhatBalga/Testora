"""Declarative base shared by every ORM model (the engine lives in infrastructure)."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
