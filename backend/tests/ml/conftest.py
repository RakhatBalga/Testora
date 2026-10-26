import pytest

from writing_synth import make_essays


@pytest.fixture
def essays():
    return make_essays()
