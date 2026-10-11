import re

from .schemas import Intent


_RULES: tuple[tuple[Intent, tuple[str, ...]], ...] = (
    ("human", ("human", "volunteer", "person", "इंसान", "व्यक्ति", "आदमी", "अधिकारी", "मानव")),
    ("task", ("remind", "reminder", "callback", "याद", "रिमाइंड", "बाद में")),
    ("scheme", ("scholarship", "scheme", "yojana", "pension", "subsidy", "eligibility", "लाभ", "छात्रवृत्ति", "योजना", "पेंशन", "पात्र")),
    ("farming", ("mandi", "wheat", "weather", "rain", "crop", "farmer", "गेहूं", "मंडी", "मौसम", "बारिश", "बरसेगा", "बरसेगी", "बरसै", "फसल", "किसान")),
    ("document", ("document", "notice", "certificate", "letter", "दस्तावेज", "दस्तावेज़", "कागज", "नोटिस", "प्रमाण पत्र", "चिट्ठी")),
)

_HINDI_NEGATION = re.compile(r"(?:नहीं|मत|ना)")
_HUMAN_TERMS = r"(?:इंसान|व्यक्ति|अधिकारी|मानव|human|volunteer|person)"


def _contains_keyword(text: str, keyword: str) -> bool:
    pattern = re.escape(keyword).replace(r"\ ", r"\s+")
    return re.search(rf"(?<![\w]){pattern}(?![\w])", text, flags=re.UNICODE) is not None


def _human_request_is_negated(text: str) -> bool:
    # Only a negation after the human term is treated as refusal.
    # This preserves phrases such as "agent नहीं, इंसान चाहिए".
    for match in re.finditer(_HUMAN_TERMS, text):
        after = text[match.end():min(len(text), match.end() + 32)]
        if _HINDI_NEGATION.search(after):
            return True
    return False


def classify_intent(message: str) -> Intent:
    text = re.sub(r"\s+", " ", message.casefold()).strip()
    for intent, keywords in _RULES:
        if intent == "human" and _human_request_is_negated(text):
            continue
        if any(_contains_keyword(text, keyword) for keyword in keywords):
            return intent
    return "general"


from dataclasses import dataclass


@dataclass(frozen=True)
class FarmingEntities:
    commodity: str | None = None
    state: str | None = None
    district: str | None = None
    market: str | None = None


_COMMODITY_ALIASES = {
    "गेहूं": "Wheat",
    "wheat": "Wheat",
    "धान": "Paddy",
    "rice": "Paddy",
    "चावल": "Paddy",
    "सरसों": "Mustard",
    "mustard": "Mustard",
    "आलू": "Potato",
    "potato": "Potato",
    "टमाटर": "Tomato",
    "tomato": "Tomato",
}

_DISTRICT_ALIASES = {
    "सोनीपत": "Sonipat",
    "sonipat": "Sonipat",
    "पानीपत": "Panipat",
    "panipat": "Panipat",
    "करनाल": "Karnal",
    "karnal": "Karnal",
    "रोहतक": "Rohtak",
    "rohtak": "Rohtak",
    "हिसार": "Hisar",
    "hisar": "Hisar",
}


def extract_farming_entities(message: str) -> FarmingEntities:
    text = re.sub(r"\s+", " ", message.casefold()).strip()
    commodity = next((value for alias, value in _COMMODITY_ALIASES.items() if _contains_keyword(text, alias)), None)
    district = next((value for alias, value in _DISTRICT_ALIASES.items() if _contains_keyword(text, alias)), None)
    state = "Haryana" if district or any(_contains_keyword(text, x) for x in ("haryana", "हरियाणा")) else None

    market = None
    if district:
        # A district followed/preceded by mandi/bazaar is a strong enough market
        # signal for the prototype; otherwise leave market unspecified.
        for alias, normalized in _DISTRICT_ALIASES.items():
            if normalized == district and re.search(rf"{re.escape(alias)}\s*(?:मंडी|mandi|market|बाजार|bazaar)", text):
                market = district
                break

    return FarmingEntities(commodity=commodity, state=state, district=district, market=market)
