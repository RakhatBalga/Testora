"""Composition edge: binds the application's ports to infrastructure.

Imported by `app.main` (and by the test suite), so the use cases never import
a concrete AI provider themselves.
"""

from app.application import ports
from app.infrastructure.ai.factory import get_speaking_grader, get_vocabulary_coach, get_writing_grader

ports.configure(
    writing_grader=get_writing_grader,
    speaking_grader=get_speaking_grader,
    vocabulary_coach=get_vocabulary_coach,
)
