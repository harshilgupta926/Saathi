from app.language_evaluation import CASES, run_language_benchmark


def test_language_benchmark_is_synthetic_and_reproducible():
    report = run_language_benchmark()
    assert len(CASES) >= 35
    assert report["total"] == len(CASES)
    assert report["kind"] == "synthetic_text_regression_not_speech_wer"
    assert 0.0 <= report["intent_accuracy"] <= 1.0
    assert 0.0 <= report["entity_field_accuracy"] <= 1.0
    assert "colloquial Hindi examples do not establish Haryanvi support" in report["limitations"]


def test_language_benchmark_covers_required_styles():
    styles = {case.language_style for case in CASES}
    assert {"hi", "hinglish", "colloquial-hi", "adversarial"} <= styles


def test_human_request_adversarial_cases_remain_explicit():
    from app.intent import classify_intent

    assert classify_intent("मुझे agent नहीं, इंसान चाहिए") == "human"
    assert classify_intent("human support चाहिए") == "human"
