

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
