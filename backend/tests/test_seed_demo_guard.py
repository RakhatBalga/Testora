from types import SimpleNamespace

import pytest

from scripts.seed import seed_demo


def _settings(monkeypatch, *, env="development", url="sqlite:///./x.db"):
    monkeypatch.setattr(
        seed_demo,
        "settings",
        SimpleNamespace(is_production=env == "production", DATABASE_URL=url),
    )


def test_seed_demo_allows_local_databases(monkeypatch):
    _settings(monkeypatch, url="postgresql://u:p@localhost:5432/testora")
    assert seed_demo._refusal_reason() is None
    _settings(monkeypatch)
    assert seed_demo._refusal_reason() is None


@pytest.mark.parametrize(
    "env,url",
    [
        ("production", "postgresql://u:p@localhost/testora"),
        ("development", "postgresql://u:p@ep-x.neon.tech/testora"),
    ],
)
def test_seed_demo_refuses_production_and_remote(monkeypatch, env, url):
    _settings(monkeypatch, env=env, url=url)
    assert seed_demo._refusal_reason()
    monkeypatch.setattr(seed_demo, "run", lambda: pytest.fail("must not run"))
    assert seed_demo.main([]) == 2


def test_seed_demo_force_flag_overrides(monkeypatch):
    _settings(monkeypatch, env="production")
    called = []
    monkeypatch.setattr(seed_demo, "run", lambda: called.append(1))
    assert seed_demo.main(["--force-i-know"]) == 0
    assert called
