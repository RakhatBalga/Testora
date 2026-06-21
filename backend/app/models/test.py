from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class Test(Base):
    __tablename__ = "tests"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    test_type = Column(String, nullable=False)  # "reading" or "listening"
    description = Column(Text, nullable=True)
    duration_minutes = Column(Integer, nullable=False, default=30)
    audio_url = Column(String, nullable=True)  # used for listening tests
    content = Column(Text, nullable=True)  # reading passage text

    questions = relationship(
        "Question", back_populates="test", cascade="all, delete-orphan"
    )


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True)
    test_id = Column(Integer, ForeignKey("tests.id"), nullable=False)
    text = Column(Text, nullable=False)
    options = Column(JSON, nullable=False)  # list of answer choices
    correct_answer = Column(String, nullable=False)
    order = Column(Integer, nullable=False, default=0)

    test = relationship("Test", back_populates="questions")
