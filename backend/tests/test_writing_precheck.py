from app.services.writing_precheck import (
    validate_writing_submission,
    zero_band_feedback,
)


VALID_TASK2_RESPONSE = (
    "Some people argue that technology has made daily life more complex. "
    "They point to constant notifications, online passwords, and the pressure "
    "to learn new systems at work. However, others believe technology has made "
    "life easier because it saves time and gives people faster access to services. "
    "In my opinion, the advantages are stronger when people use digital tools "
    "carefully and avoid unnecessary distractions."
)


def test_cyrillic_response_is_zero_band_without_ai():
    precheck = validate_writing_submission(
        task_type=2,
        text="аывпывпывпывпапывпвыапывпвывпвывпвывпапыв",
        min_words=250,
    )

    assert precheck.valid is False
    assert precheck.reason_code == "not_english"
    assert precheck.word_count == 0

    feedback = zero_band_feedback(2, precheck)
    assert feedback.error is False
    assert feedback.band == 0.0
    assert set(feedback.criteria.values()) == {0.0}


def test_tiny_english_response_is_zero_band_without_ai():
    precheck = validate_writing_submission(
        task_type=2,
        text="Technology is good.",
        min_words=250,
    )

    assert precheck.valid is False
    assert precheck.reason_code == "too_short"


def test_single_sentence_response_is_not_a_real_task2_attempt():
    text = (
        "Technology can make life easier because people can communicate, study, "
        "work, buy products, use maps, pay bills, and get information very fast "
        "from almost any place in the world, while online lessons, hospital "
        "appointments, banking applications, public transport tools, and digital "
        "documents also reduce many small delays that used to make ordinary life "
        "more difficult for families, workers, students, and older people"
    )

    precheck = validate_writing_submission(task_type=2, text=text, min_words=250)

    assert precheck.valid is False
    assert precheck.reason_code == "too_few_sentences"


def test_reasonable_english_response_passes_precheck():
    precheck = validate_writing_submission(
        task_type=2,
        text=VALID_TASK2_RESPONSE,
        min_words=250,
    )

    assert precheck.valid is True
    assert precheck.word_count >= 60
    assert precheck.sentence_count >= 3
