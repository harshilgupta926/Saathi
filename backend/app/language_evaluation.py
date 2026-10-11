"""Small, deterministic language regression set for Saathi.

This is a text-level smoke benchmark, not a speech WER claim. The phrases are
synthetic and contain no real user data. Expected labels represent intended
meaning, so misses remain visible in the report instead of being relabelled as
successes.
"""
from __future__ import annotations

from dataclasses import dataclass

from .intent import classify_intent, extract_farming_entities


@dataclass(frozen=True)
class LanguageCase:
    text: str
    language_style: str
    expected_intent: str
    expected_commodity: str | None = None
    expected_district: str | None = None


CASES: tuple[LanguageCase, ...] = (
    LanguageCase("सोनीपत मंडी में गेहूं का भाव बताओ", "hi", "farming", "Wheat", "Sonipat"),
    LanguageCase("कल बारिश होगी क्या", "hi", "farming"),
    LanguageCase("मुझे किसी इंसान से बात करनी है", "hi", "human"),
    LanguageCase("मुझे किसान योजना की जानकारी चाहिए", "hi", "scheme"),
    LanguageCase("इस नोटिस को समझा दो", "hi", "document"),
    LanguageCase("मुझे कल याद दिलाना", "hi", "task"),
    LanguageCase("पानीपत में सरसों का रेट क्या है", "hi", "farming", "Mustard", "Panipat"),
    LanguageCase("नमस्ते साथी", "hi", "general"),
    LanguageCase("किसी अधिकारी से बात करवाओ", "hi", "human"),
    LanguageCase("छात्रवृत्ति के लिए कौन पात्र है", "hi", "scheme"),
    LanguageCase("Sonipat mandi me wheat ka bhav batao", "hinglish", "farming", "Wheat", "Sonipat"),
    LanguageCase("kal rain hogi kya", "hinglish", "farming"),
    LanguageCase("mujhe human se baat karni hai", "hinglish", "human"),
    LanguageCase("PM Kisan scheme kaise milegi", "hinglish", "scheme"),
    LanguageCase("ye notice explain kar do", "hinglish", "document"),
    LanguageCase("kal mujhe remind kar dena", "hinglish", "task"),
    LanguageCase("Panipat me mustard rate kya hai", "hinglish", "farming", "Mustard", "Panipat"),
    LanguageCase("hello Saathi", "hinglish", "general"),
    LanguageCase("agent nahi, insaan chahiye", "hinglish", "human"),
    LanguageCase("pension eligibility batao", "hinglish", "scheme"),
    LanguageCase("गेहूं का भाव बता दे भाई", "colloquial-hi", "farming", "Wheat"),
    LanguageCase("कल पानी बरसेगा के", "colloquial-hi", "farming"),
    LanguageCase("मन्ने आदमी तै बात करनी सै", "colloquial-hi", "human"),
    LanguageCase("किसान वाली योजना बता दे", "colloquial-hi", "scheme"),
    LanguageCase("इस कागज में के लिख्या सै", "colloquial-hi", "document"),
    LanguageCase("मन्ने फेर याद करा दियो", "colloquial-hi", "task"),
    LanguageCase("रोहतक में आलू का भाव बता", "colloquial-hi", "farming", "Potato", "Rohtak"),
    LanguageCase("राम राम साथी", "colloquial-hi", "general"),
    LanguageCase("मन्ने volunteer से बात करवा दे", "colloquial-hi", "human"),
    LanguageCase("सरकारी लाभ कैसे मिलेगा", "colloquial-hi", "scheme"),
    LanguageCase("मुझे agent नहीं, इंसान चाहिए", "adversarial", "human"),
    LanguageCase("इंसान से बात नहीं करनी", "adversarial", "general"),
    LanguageCase("मंडी का भाव बताओ", "adversarial", "farming"),
    LanguageCase("गेहूं का भाव सोनीपत में", "adversarial", "farming", "Wheat", "Sonipat"),
    LanguageCase("weather batao", "adversarial", "farming"),
    LanguageCase("मुझे मदद चाहिए", "adversarial", "general"),
    LanguageCase("document ka matlab batao", "adversarial", "document"),
    LanguageCase("callback ka reminder chahiye", "adversarial", "task"),
    LanguageCase("human support चाहिए", "adversarial", "human"),
    LanguageCase("subsidy ki eligibility batao", "adversarial", "scheme"),
)


def run_language_benchmark() -> dict[str, object]:
    """Return reproducible text metrics; never represent them as audio metrics."""
    total = len(CASES)
    correct_intents = 0
    entity_checks = 0
    entity_correct = 0
    by_style: dict[str, dict[str, int]] = {}

    for case in CASES:
        predicted = classify_intent(case.text)
        style = by_style.setdefault(case.language_style, {"correct": 0, "total": 0})
        style["total"] += 1
        if predicted == case.expected_intent:
            correct_intents += 1
            style["correct"] += 1

        entities = extract_farming_entities(case.text)
        for field, expected in (
            ("commodity", case.expected_commodity),
            ("district", case.expected_district),
        ):
            if expected is not None:
                entity_checks += 1
                if getattr(entities, field) == expected:
                    entity_correct += 1

    return {
        "kind": "synthetic_text_regression_not_speech_wer",
        "total": total,
        "intent_correct": correct_intents,
        "intent_accuracy": correct_intents / total if total else 0.0,
        "entity_fields_correct": entity_correct,
        "entity_fields_checked": entity_checks,
        "entity_field_accuracy": entity_correct / entity_checks if entity_checks else 0.0,
        "by_language_style": {
            style: {
                **counts,
                "accuracy": counts["correct"] / counts["total"] if counts["total"] else 0.0,
            }
            for style, counts in sorted(by_style.items())
        },
        "limitations": [
            "synthetic text only; no audio or word-error-rate measurement",
            "colloquial Hindi examples do not establish Haryanvi support",
            "small regression set; not a representative field evaluation",
        ],
    }
