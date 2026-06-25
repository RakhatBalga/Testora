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
    difficulty = Column(String, nullable=True)  # "Easy" | "Medium" | "Hard"

    sections = relationship(
        "Section",
        back_populates="test",
        cascade="all, delete-orphan",
        order_by="Section.order",
    )


class Section(Base):
    __tablename__ = "sections"

    id = Column(Integer, primary_key=True)
    test_id = Column(Integer, ForeignKey("tests.id"), nullable=False)
    order = Column(Integer, nullable=False, default=0)
    title = Column(String, nullable=False)
    instructions = Column(Text, nullable=True)
    passage = Column(Text, nullable=True)  # reading passage
    audio_url = Column(String, nullable=True)  # listening audio

    test = relationship("Test", back_populates="sections")
    questions = relationship(
        "Question",
        back_populates="section",
        cascade="all, delete-orphan",
        order_by="Question.order",
    )


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True)
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=False)
    order = Column(Integer, nullable=False, default=0)
    text = Column(Text, nullable=False)
    # single_choice | multiple_choice | true_false_notgiven | matching | fill_blank | short_answer
    question_type = Column(String, nullable=False, default="single_choice")
    options = Column(JSON, nullable=True)  # list of choices (null for free-text)
    correct_answer = Column(JSON, nullable=False)  # list of acceptable answers
    explanation = Column(Text, nullable=True)  # shown in review mode (why the answer is right)
    # Where the answer is supported in the passage — list of {paragraph, text}
    # spans, used by Reading Review to highlight evidence. Null for question
    # types with no passage support (e.g. Not Given) or un-authored content.
    evidence = Column(JSON, nullable=True)

    section = relationship("Section", back_populates="questions")
