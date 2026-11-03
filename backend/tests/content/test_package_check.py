import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from content_tools.check_package import check_package


def package():
    return {
        "tests": [
            {
                "title": "Practice",
                "test_type": "reading",
                "content_version": "1",
                "duration_minutes": 20,
                "metadata": {"published": False},
                "sections": [
                    {
                        "title": "Passage",
                        "passage": "Original text",
                        "questions": [
                            {"text": "Question", "question_type": "short_answer", "correct_answer": ["answer"]}
                        ],
                    }
                ],
            }
        ]
    }


def test_offline_cli_does_not_load_app_or_database(tmp_path):
    path = tmp_path / "pack.json"
    path.write_text(json.dumps(package()))
    code = """import runpy, sys
class BlockApp:
    def find_spec(self, fullname, *args):
        if fullname == 'app' or fullname.startswith(('app.', 'sqlalchemy', 'psycopg')):
            raise AssertionError('Database/application import attempted')
sys.meta_path.insert(0, BlockApp())
sys.argv = ['check_package', sys.argv[1]]
runpy.run_module('content_tools.check_package', run_name='__main__')
"""
    env = {k: v for k, v in os.environ.items() if k not in {"DATABASE_URL", "SECRET_KEY"}}
    result = subprocess.run(
        [sys.executable, "-c", code, str(path)], cwd=Path(__file__).parents[2], env=env, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["database_access"] is False


@pytest.mark.parametrize("data", [None, [], {}, {"tests": []}, {"tests": [None]}, {"tests": [{"sections": [None]}]}])
def test_malformed_packages_report_errors(data, tmp_path):
    assert check_package(data, tmp_path)


def test_publication_requires_evidence_and_strict_boolean(tmp_path):
    data = package()
    meta = data["tests"][0]["metadata"]
    meta["published"] = "true"
    assert check_package(data, tmp_path)
    meta["published"] = True
    assert check_package(data, tmp_path)
    meta["rights"] = {"publication_allowed": True, "evidence": "Author agreement reference A1"}
    assert not check_package(data, tmp_path)


def test_empty_answers_and_duplicate_questions_rejected(tmp_path):
    data = package()
    questions = data["tests"][0]["sections"][0]["questions"]
    questions[0]["correct_answer"] = []
    questions[0]["order"] = 1
    questions.append(dict(questions[0]))
    errors = check_package(data, tmp_path)
    assert any("answer list" in e for e in errors)
    assert any("unique" in e for e in errors)


def test_audio_cannot_escape_asset_directory(tmp_path):
    data = package()
    data["tests"][0]["test_type"] = "listening"
    data["tests"][0]["sections"][0]["audio_url"] = "/static/audio/../../private.wav"
    (tmp_path / "private.wav").write_bytes(b"private")
    assert any("outside" in e for e in check_package(data, tmp_path))


def test_choice_key_must_reference_an_option(tmp_path):
    data = package()
    question = data["tests"][0]["sections"][0]["questions"][0]
    question.update(question_type="single_choice", options=["First", "Second"], correct_answer=["Z"])
    assert any("match an option" in e for e in check_package(data, tmp_path))
    question["correct_answer"] = ["B"]
    assert not check_package(data, tmp_path)
