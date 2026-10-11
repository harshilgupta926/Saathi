from __future__ import annotations

import re
from dataclasses import dataclass

from .config import get_settings
from .escalation import EscalationPolicy, EscalationReason
from .http_tools import DataGovMandiTool, OpenMeteoWeatherTool
from .provider_adapters import GeminiToolRouter
from .intent import classify_intent, extract_farming_entities
from .provenance import ToolResult
from .schemas import Intent, LocationContext
from .tools import DemoMandiTool, DemoWeatherTool, PMKisanSchemeTool


@dataclass(frozen=True)
class AgentContext:
    household_id: str | None
    language: str = "hi"
    location: LocationContext | None = None


@dataclass(frozen=True)
class AgentOutcome:
    intent: Intent
    reply: str
    result: ToolResult | None
    confidence: float
    escalated: bool
    escalation_reason: EscalationReason | None
    tool_name: str | None = None
    results: tuple[ToolResult, ...] = ()


class ToolPolicy:
    """Server-side capability gate: intent may suggest, policy decides what can run."""

    ALLOWED: dict[Intent, frozenset[str]] = {
        "farming": frozenset({"get_mandi_price", "get_weather"}),
        "scheme": frozenset({"get_pmkisan_info"}),
        "human": frozenset({"request_human"}),
        "document": frozenset(),
        "task": frozenset(),
        "general": frozenset(),
    }

    @classmethod
    def permits(cls, intent: Intent, tool_name: str) -> bool:
        return tool_name in cls.ALLOWED.get(intent, frozenset())


class Orchestrator:
    def __init__(self) -> None:
        settings = get_settings()
        if settings.demo_mode:
            self.weather = DemoWeatherTool()
            self.mandi = DemoMandiTool()
        else:
            self.weather = OpenMeteoWeatherTool()
            self.mandi = (
                DataGovMandiTool(
                    api_key=settings.mandi_api_key,
                    resource_id=settings.mandi_resource_id,
                    api_base=settings.mandi_api_base,
                )
                if settings.mandi_api_key and settings.mandi_resource_id
                else None
            )
        self.escalation = EscalationPolicy()
        self.scheme = PMKisanSchemeTool()
        self.reasoning_router = GeminiToolRouter(settings.gemini_api_key, settings.llm_model) if settings.gemini_api_key and not settings.demo_mode else None

    def _tool_name(self, intent: Intent, tool_name: str) -> str:
        if not ToolPolicy.permits(intent, tool_name):
            raise RuntimeError(f"tool_not_permitted:{intent}:{tool_name}")
        return tool_name

    def _outcome(
        self,
        *,
        intent: Intent,
        reply: str,
        result: ToolResult | None = None,
        confidence: float = 0.9,
        explicit_human_request: bool = False,
        safety_boundary: bool = False,
        tool_name: str | None = None,
        results: tuple[ToolResult, ...] = (),
    ) -> AgentOutcome:
        decision = self.escalation.evaluate(
            confidence=confidence,
            explicit_human_request=explicit_human_request,
            provider_failed=bool(result and not result.ok) or any(not item.ok for item in results),
            safety_boundary=safety_boundary,
        )
        return AgentOutcome(
            intent=intent,
            reply=reply,
            result=result,
            confidence=decision.confidence,
            escalated=decision.escalate,
            escalation_reason=decision.reason,
            tool_name=tool_name,
            results=results or ((result,) if result else ()),
        )

    async def handle(self, message: str, context: AgentContext) -> AgentOutcome:
        intent = classify_intent(message)

        # Optional reasoning-provider assist. The provider may select only a declared
        # capability; deterministic adapters still own factual execution and validation.
        if self.reasoning_router is not None:
            try:
                selected = await self.reasoning_router.choose(message)
                if selected and selected.name == "request_human":
                    return self._outcome(
                        intent="human",
                        reply="ठीक है। मैं आपकी बात volunteer सहायता के लिए भेजने की तैयारी कर रहा हूँ।",
                        confidence=0.95,
                        explicit_human_request=True,
                        tool_name=self._tool_name("human", "request_human"),
                    )
                if selected and selected.name == "get_weather" and intent == "farming" and context.location is not None:
                    args = selected.arguments
                    latitude = float(args.get("latitude", context.location.latitude))
                    longitude = float(args.get("longitude", context.location.longitude))
                    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
                        raise ValueError("reasoning_provider_invalid_location")
                    result = await self.weather.forecast(latitude=latitude, longitude=longitude)
                    if result.ok:
                        data = result.data
                        probability = data.get("rain_probability_pct", data.get("next_24h_rain_probability_max", 0))
                        return self._outcome(
                            intent="farming",
                            reply=f"उपलब्ध मौसम जानकारी के अनुसार तापमान {data['temperature_c']}°C है और अगले 24 घंटे में बारिश की अधिकतम संभावना {probability}% है।",
                            result=result,
                            confidence=0.9,
                            tool_name="get_weather",
                        )
                if selected and selected.name == "get_mandi_price" and intent == "farming" and self.mandi is not None:
                    args = selected.arguments
                    commodity = str(args.get("commodity") or "").strip()
                    state = str(args.get("state") or "").strip()
                    district = str(args.get("district") or "").strip() or None
                    if commodity and state:
                        result = await self.mandi.price(commodity=commodity, state=state, district=district)
                        if result.ok:
                            data = result.data
                            market = data.get("market") or district or state
                            date = data.get("arrival_date") or "latest returned date"
                            return self._outcome(
                                intent="farming",
                                reply=f"सरकारी बाजार डेटा के अनुसार {market} में {data['commodity']} का मॉडल भाव ₹{data['modal_price']} प्रति क्विंटल है (डेटा दिनांक {date})।",
                                result=result,
                                confidence=0.9,
                                tool_name="get_mandi_price",
                            )
            except (ValueError, TypeError, RuntimeError):
                pass

        if intent == "human":
            return self._outcome(
                intent=intent,
                reply="ठीक है। मैं आपकी बात volunteer सहायता के लिए भेजने की तैयारी कर रहा हूँ।",
                confidence=1.0,
                explicit_human_request=True,
                tool_name=self._tool_name(intent, "request_human"),
            )

        if intent == "farming":
            lowered = message.casefold()

            def contains_term(term: str) -> bool:
                return re.search(
                    rf"(?<![\w\u0900-\u097F]){re.escape(term)}(?![\w\u0900-\u097F])",
                    lowered,
                    flags=re.UNICODE,
                ) is not None

            # Use term boundaries here. Plain substring matching makes words such
            # as "संभावना" accidentally match the mandi signal "भाव".
            wants_weather = any(contains_term(x) for x in ("मौसम", "बारिश", "weather", "rain"))
            wants_mandi = any(contains_term(x) for x in ("मंडी", "mandi", "भाव", "रेट", "price", "bhav"))
            if wants_weather and wants_mandi:
                location = context.location
                if location is None:
                    return self._outcome(
                        intent=intent,
                        reply="मंडी का भाव तो देखा जा सकता है, लेकिन मौसम के लिए आपका शहर या स्थान चाहिए। कृपया अपना जिला या स्थान बताइए।",
                        confidence=0.72,
                        tool_name=self._tool_name(intent, "get_weather"),
                    )
                entities = extract_farming_entities(message)
                missing = []
                if not entities.commodity:
                    missing.append("फसल")
                if not entities.state:
                    missing.append("राज्य")
                if not entities.district and not entities.market:
                    missing.append("जिला या मंडी")
                if missing:
                    return self._outcome(
                        intent=intent,
                        reply="मंडी और मौसम दोनों सही बताने के लिए " + " और ".join(missing) + " बताइए।",
                        confidence=0.78,
                        tool_name=self._tool_name(intent, "get_mandi_price"),
                    )
                weather_result = await self.weather.forecast(latitude=location.latitude, longitude=location.longitude)
                mandi_result = (
                    await self.mandi.price(
                        commodity=entities.commodity,
                        state=entities.state,
                        district=entities.district,
                        market=entities.market,
                    )
                    if self.mandi is not None
                    else ToolResult(
                        ok=False,
                        error_code="MANDI_PROVIDER_NOT_CONFIGURED",
                        retryable=False,
                        data={},
                    )
                )
                parts = []
                if mandi_result.ok:
                    d = mandi_result.data
                    market = d.get("market") or entities.market or entities.district or entities.state
                    date = d.get("arrival_date") or "latest returned date"
                    parts.append(f"सरकारी बाजार डेटा के अनुसार {market} में {d['commodity']} का मॉडल भाव ₹{d['modal_price']} प्रति क्विंटल है (डेटा दिनांक {date})।")
                else:
                    parts.append("सरकारी मंडी स्रोत से इस अनुरोध के लिए विश्वसनीय भाव नहीं मिला, इसलिए मैं भाव का अनुमान नहीं दूँगा।")
                if weather_result.ok:
                    d = weather_result.data
                    probability = d.get("rain_probability_pct", d.get("next_24h_rain_probability_max", 0))
                    parts.append(f"उपलब्ध मौसम जानकारी के अनुसार तापमान {d['temperature_c']}°C है और अगले 24 घंटे में बारिश की अधिकतम संभावना {probability}% है।")
                else:
                    parts.append("मौसम की जानकारी अभी उपलब्ध नहीं है, इसलिए मैं बारिश की संभावना का अनुमान नहीं दूँगा।")
                return self._outcome(
                    intent=intent,
                    reply=" ".join(parts),
                    result=mandi_result if mandi_result.ok else weather_result,
                    results=(mandi_result, weather_result),
                    confidence=0.9 if mandi_result.ok and weather_result.ok else 0.6,
                    tool_name="get_mandi_price+get_weather",
                )

            if wants_weather:
                location = context.location
                if location is None:
                    return self._outcome(
                        intent=intent,
                        reply="मौसम बताने के लिए आपका शहर या स्थान चाहिए। कृपया अपना जिला या स्थान बताइए।",
                        confidence=0.72,
                        tool_name="get_weather",
                    )
                result = await self.weather.forecast(latitude=location.latitude, longitude=location.longitude)
                if result.ok:
                    d = result.data
                    probability = d.get("rain_probability_pct", d.get("next_24h_rain_probability_max", 0))
                    return self._outcome(
                        intent=intent,
                        reply=f"उपलब्ध मौसम जानकारी के अनुसार तापमान {d['temperature_c']}°C है और अगले 24 घंटे में बारिश की अधिकतम संभावना {probability}% है।",
                        result=result,
                        tool_name="get_weather",
                    )
                return self._outcome(
                    intent=intent,
                    reply="अभी मौसम की जानकारी उपलब्ध नहीं है। मैं गलत जानकारी नहीं देना चाहता।",
                    result=result,
                    confidence=0.55,
                    tool_name="get_weather",
                )

            if self.mandi is None:
                return self._outcome(
                    intent=intent,
                    reply="मंडी का लाइव सरकारी स्रोत अभी configured नहीं है। मैं डेमो भाव को live भाव बताकर नहीं दिखाऊँगा।",
                    confidence=0.55,
                    tool_name="get_mandi_price",
                )

            entities = extract_farming_entities(message)
            missing = []
            if not entities.commodity:
                missing.append("फसल")
            if not entities.state:
                missing.append("राज्य")
            if not entities.district and not entities.market:
                missing.append("जिला या मंडी")

            if missing:
                return self._outcome(
                    intent=intent,
                    reply="मंडी का सही सरकारी भाव बताने के लिए " + " और ".join(missing) + " बताइए।",
                    confidence=0.78,
                    tool_name="get_mandi_price",
                )

            result = await self.mandi.price(
                commodity=entities.commodity,
                state=entities.state,
                district=entities.district,
                market=entities.market,
            )
            if result.ok:
                d = result.data
                market = d.get("market") or entities.market or entities.district or entities.state
                date = d.get("arrival_date") or "latest returned date"
                return self._outcome(
                    intent=intent,
                    reply=f"सरकारी बाजार डेटा के अनुसार {market} में {d['commodity']} का मॉडल भाव ₹{d['modal_price']} प्रति क्विंटल है (डेटा दिनांक {date})।",
                    result=result,
                    tool_name="get_mandi_price",
                )
            return self._outcome(
                intent=intent,
                reply="अभी सरकारी मंडी स्रोत से विश्वसनीय भाव नहीं मिला। मैं अनुमान नहीं दूँगा।",
                result=result,
                confidence=0.55,
                tool_name="get_mandi_price",
            )

        if intent == "scheme" and any(x in message.casefold() for x in ("किसान", "pm-kisan", "pm kisan", "किसान योजना")):
            result = await self.scheme.explain()
            return self._outcome(
                intent=intent,
                reply="आधिकारिक PM-KISAN जानकारी के अनुसार पात्र landholding farmer families के लिए सालाना ₹6,000 तीन बराबर किस्तों में दिए जाते हैं और registered farmers के लिए eKYC mandatory है। अंतिम eligibility सरकार की scheme guidelines और verification पर निर्भर है।",
                result=result,
                confidence=0.96,
                tool_name=self._tool_name(intent, "get_pmkisan_info"),
            )

        replies = {
            "scheme": "मैं सरकारी योजनाओं की पात्रता और जरूरी दस्तावेज़ समझाने में मदद कर सकता हूँ।",
            "document": "मैं दस्तावेज़ का पाठ समझाने और जरूरी अगला कदम निकालने में मदद कर सकता हूँ।",
            "task": "मैं इसे आपके लिए follow-up task के रूप में रखने में मदद कर सकता हूँ।",
            "general": "नमस्ते! मैं साथी हूँ। आप अपनी जरूरत हिंदी में बताइए।",
        }
        return self._outcome(intent=intent, reply=replies[intent])
