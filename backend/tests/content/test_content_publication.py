from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.routers.tests import get_test, list_tests
from app.application.attempts import submit_reading
from app.application.listening.service import get_published_test, list_catalog
from app.domain.models.test import Test as ContentTest
from app.domain.models.attempt import Attempt
from app.domain.publication import is_published


@pytest.mark.parametrize("skill", ["reading", "listening"])
@pytest.mark.parametrize(
    "metadata",
    [
        None,
        {},
        [],
        {"published": False},
        {"published": "true"},
        {"published": 1},
        {"published": True, "superseded_by": "v2"},
    ],
)
def test_hidden_content_is_rejected_even_by_direct_id(api, skill, metadata):
    with api.Session() as db:
        test = ContentTest(title="IELTS Academic Reading - Test 01", test_type=skill, content_metadata=metadata)
        db.add(test)
        db.commit()
        assert not is_published(test)
        assert not list_tests(db=db, current_user=SimpleNamespace(id=api.user_id))
        for call in (
            lambda: get_test(test.id, db=db, current_user=SimpleNamespace(id=api.user_id)),
            lambda: submit_reading(db, SimpleNamespace(id=api.user_id), SimpleNamespace(test_id=test.id)),
            lambda: get_published_test(db, test.id),
        ):
            with pytest.raises(HTTPException) as exc:
                call()
            assert exc.value.status_code == 404
        assert db.query(Attempt).count() == 0


@pytest.mark.parametrize("skill", ["reading", "listening"])
def test_published_content_does_not_depend_on_title(api, skill):
    with api.Session() as db:
        test = ContentTest(title="New original practice", test_type=skill, content_metadata={"published": True})
        db.add(test)
        db.commit()
        assert [t["id"] for t in list_tests(db=db, current_user=SimpleNamespace(id=api.user_id))] == [test.id]
        get_test(test.id, db=db, current_user=SimpleNamespace(id=api.user_id))
        if skill == "listening":
            assert [t["id"] for t in list_catalog(db)] == [test.id]
            assert get_published_test(db, test.id).id == test.id
