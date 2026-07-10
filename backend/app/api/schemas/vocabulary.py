from pydantic import BaseModel, Field


class SaveWordIn(BaseModel):
    word: str = Field(..., min_length=1, max_length=80)
    context: str | None = Field(None, max_length=2000)
    source: str | None = Field(None, max_length=40)
    source_ref: str | None = Field(None, max_length=100)


class TrainingIn(BaseModel):
    training: bool


class QuizSubmitIn(BaseModel):
    # One selected option index per question (None = left blank).
    answers: list[int | None] = Field(default_factory=list)
