from sqlalchemy import Column, Float, Integer, String
from app.infrastructure.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    target_band = Column(Float, nullable=False, default=7.5)
