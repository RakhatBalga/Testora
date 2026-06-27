from types import SimpleNamespace

from app.api.routers.tests import is_catalog_test


def _test(title: str, test_type: str = "reading", published: bool = False):
    return SimpleNamespace(title=title, test_type=test_type, content_metadata={"published": published})


def test_canonical_reading_tests_are_listed():
    assert is_catalog_test(_test("IELTS Academic Reading — Test 01"))
    assert is_catalog_test(_test("IELTS Academic Reading - Test 10"))


def test_legacy_reading_tests_are_hidden_from_catalog():
    assert not is_catalog_test(_test("IELTS Academic Reading — Test A"))
    assert not is_catalog_test(_test("Academic Reading Test 1 (Full)"))


def test_non_reading_tests_are_not_filtered_by_reading_catalog_rule():
    assert not is_catalog_test(_test("IELTS Listening Placeholder", "listening"))
    assert is_catalog_test(_test("Testora Listening", "listening", published=True))
