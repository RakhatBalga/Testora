

import traceback
import pytest
from ml.data import ResponseRecord, read_jsonl, write_report

def test_invalid_record_traceback_hides_payload(tmp_path):
    source = tmp_path / 'private.jsonl'
    source.write_text('{"email": "private@example.test"}', encoding='utf-8')
    try:
        read_jsonl(source, ResponseRecord)
    except ValueError:
        text = traceback.format_exc()
        assert 'private@example.test' not in text
        assert 'line 1' in text
    else:
        pytest.fail('Invalid record accepted')


@pytest.mark.parametrize('field', ['response_id', 'learner_id', 'item_id', 'content_version', 'question_type'])
def test_blank_response_identifiers_rejected(field):
    row = dict(response_id='r', learner_id='u', item_id='q', content_version='v1',
               question_type='choice', skill='reading', correct=True, answered_at='2026-01-01T00:00:00Z')
    row[field] = '  '
    with pytest.raises(ValueError):
        ResponseRecord(**row)


def test_report_never_overwrites_existing_result(tmp_path):
    path = tmp_path / 'report.json'
    write_report(path, {'value': 1})
    before = path.read_bytes()
    with pytest.raises(FileExistsError):
        write_report(path, {'value': 2})
    assert path.read_bytes() == before
    invalid = tmp_path / 'invalid.json'
    with pytest.raises(ValueError):
        write_report(invalid, {'value': float('nan')})
    assert not invalid.exists()
