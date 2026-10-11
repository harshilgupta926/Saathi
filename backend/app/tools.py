from datetime import datetime, timedelta, timezone
from typing import Protocol

from .provenance import SourceRecord, ToolResult


class WeatherTool(Protocol):
    async def forecast(self, *, latitude: float, longitude: float) -> ToolResult: ...


class MandiTool(Protocol):
    async def price(self, *, commodity: str, state: str, district: str | None = None, market: str | None = None) -> ToolResult: ...


class DemoWeatherTool:
    async def forecast(self, *, latitude: float, longitude: float) -> ToolResult:
        return ToolResult(
            ok=True,
            data={
                "condition": "Partly cloudy",
                "temperature_c": 28,
                "rain_probability_pct": 20,
                "tomorrow_date": (datetime.now(timezone.utc) + timedelta(days=1)).date().isoformat(),
                "tomorrow_rain_probability_pct": 20,
                "tomorrow_precipitation_mm": 0,
                "latitude": latitude,
                "longitude": longitude,
            },
            source=SourceRecord(
                name="Saathi Demo Weather",
                url="https://open-meteo.com/",
                retrieved_at=datetime.now(timezone.utc),
                freshness_note="DEMO DATA — replace with live provider before production.",
            ),
        )


class DemoMandiTool:
    async def price(self, *, commodity: str, state: str, district: str | None = None, market: str | None = None) -> ToolResult:
        return ToolResult(
            ok=True,
            data={
                "commodity": commodity,
                "market": market or district or state,
                "min_price": 2100,
                "modal_price": 2250,
                "max_price": 2325,
                "unit": "INR/quintal",
            },
            source=SourceRecord(
                name="Saathi Demo Mandi",
                url="https://data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi",
                retrieved_at=datetime.now(timezone.utc),
                freshness_note="DEMO DATA — not a live market quote.",
            ),
        )


class PMKisanSchemeTool:
    """Small, source-backed PM-KISAN explainer.

    This intentionally explains the official scheme and links the user to the
    government portal; it does not claim eligibility without the required
    household facts or perform Aadhaar/OTP actions.
    """

    async def explain(self) -> ToolResult:
        return ToolResult(
            ok=True,
            data={
                "scheme": "PM-KISAN Samman Nidhi",
                "benefit": "₹6,000 per year in three equal installments for eligible landholding farmer families",
                "ekyc": "eKYC is mandatory for registered PM-KISAN farmers",
                "verification": "Eligibility is determined under the scheme guidelines and state/UT identification process",
                "next_step": "Use the official PM-KISAN Know Your Status or New Farmer Registration flow; do not share Aadhaar or OTP with Saathi.",
            },
            source=SourceRecord(
                name="PM-KISAN · Government of India",
                url="https://pmkisan.gov.in/",
                retrieved_at=datetime.now(timezone.utc),
                freshness_note="Official government portal; scheme rules and portal status can change. Saathi does not make final eligibility decisions.",
            ),
        )
