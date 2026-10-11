from datetime import datetime, timezone

import httpx

from .provenance import SourceRecord, ToolResult


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


class OpenMeteoWeatherTool:
    def __init__(self, timeout_seconds: float = 5.0) -> None:
        self.timeout_seconds = timeout_seconds

    async def forecast(self, *, latitude: float, longitude: float) -> ToolResult:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,precipitation",
            "hourly": "precipitation_probability,temperature_2m",
            "daily": "precipitation_probability_max,precipitation_sum",
            "forecast_days": 2,
            "forecast_hours": 24,
            "timezone": "auto",
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(OPEN_METEO_URL, params=params)
                response.raise_for_status()
                payload = response.json()

            current = payload.get("current", {})
            hourly = payload.get("hourly", {})
            probabilities = hourly.get("precipitation_probability", [])
            temperature = current.get("temperature_2m")
            precipitation = current.get("precipitation")
            rain_probability = max(probabilities or [0])
            daily = payload.get("daily", {})
            daily_dates = daily.get("time") or []
            daily_probabilities = daily.get("precipitation_probability_max") or []
            daily_precipitation = daily.get("precipitation_sum") or []
            tomorrow_probability = daily_probabilities[1] if len(daily_probabilities) > 1 else None
            tomorrow_precipitation = daily_precipitation[1] if len(daily_precipitation) > 1 else None
            tomorrow_date = daily_dates[1] if len(daily_dates) > 1 else None

            if temperature is None or not probabilities:
                raise ValueError("weather_payload_missing_required_fields")

            return ToolResult(
                ok=True,
                data={
                    "latitude": latitude,
                    "longitude": longitude,
                    "temperature_c": temperature,
                    "precipitation_mm": precipitation,
                    "rain_probability_pct": rain_probability,
                    "next_24h_rain_probability_max": rain_probability,
                    "tomorrow_date": tomorrow_date,
                    "tomorrow_rain_probability_pct": tomorrow_probability,
                    "tomorrow_precipitation_mm": tomorrow_precipitation,
                },
                source=SourceRecord(
                    name="Open-Meteo",
                    url=OPEN_METEO_URL,
                    retrieved_at=datetime.now(timezone.utc),
                    freshness_note="LIVE provider response; forecast values can change.",
                ),
            )
        except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
            return ToolResult(
                ok=False,
                error_code="WEATHER_PROVIDER_ERROR",
                retryable=True,
                data={"detail": type(exc).__name__, "latitude": latitude, "longitude": longitude},
            )


class DataGovMandiTool:
    """AGMARKNET-backed OGD adapter.

    The OGD resource id and API key are configuration, not source-code constants.
    This keeps demo builds deterministic while allowing a real government resource
    to be enabled without changing orchestration code.
    """

    def __init__(
        self,
        *,
        api_key: str,
        resource_id: str,
        api_base: str = "https://api.data.gov.in/resource",
        timeout_seconds: float = 8.0,
    ) -> None:
        self.api_key = api_key
        self.resource_id = resource_id
        self.api_base = api_base.rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def price(self, *, commodity: str, state: str, district: str | None = None, market: str | None = None) -> ToolResult:
        url = f"{self.api_base}/{self.resource_id}"
        filters = {"state.keyword": state, "commodity": commodity}
        if district:
            filters["district"] = district
        if market:
            filters["market"] = market

        params = {
            "api-key": self.api_key,
            "format": "json",
            "limit": 25,
            "sort[arrival_date]": "desc",
            **{f"filters[{key}]": value for key, value in filters.items()},
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                payload = response.json()

            records = payload.get("records") or []
            if not records:
                return ToolResult(
                    ok=False,
                    error_code="MANDI_NO_RECORDS",
                    retryable=False,
                    data={"commodity": commodity, "state": state, "district": district},
                    source=SourceRecord(
                        name="Government OGD / AGMARKNET",
                        url=url,
                        retrieved_at=datetime.now(timezone.utc),
                        freshness_note="Government dataset queried; no matching record returned.",
                    ),
                )

            def norm(value: object) -> str:
                return " ".join(str(value or "").casefold().split())

            def record_field(record: dict, *keys: str):
                for key in keys:
                    if record.get(key) not in (None, ""):
                        return record[key]
                return None

            requested_commodity = norm(commodity)
            requested_state = norm(state)
            requested_district = norm(district)
            requested_market = norm(market)

            def score(record: dict) -> int:
                score = 0
                if norm(record_field(record, "commodity", "Commodity")) == requested_commodity:
                    score += 4
                if norm(record_field(record, "state", "State")) == requested_state:
                    score += 3
                if requested_district and norm(record_field(record, "district", "District")) == requested_district:
                    score += 3
                if requested_market and norm(record_field(record, "market", "Market")) == requested_market:
                    score += 5
                return score

            def arrival_date(record: dict) -> datetime:
                value = record_field(record, "arrival_date", "Arrival_Date", "arrival date")
                if not value:
                    return datetime.min.replace(tzinfo=timezone.utc)
                text = str(value).strip()
                for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y"):
                    try:
                        return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
                    except ValueError:
                        continue
                return datetime.min.replace(tzinfo=timezone.utc)

            # Prefer the strongest entity match, then the newest dated record.
            # Never let upstream response ordering decide which market/date is shown.
            scored_records = sorted(
                ((score(record), arrival_date(record), record) for record in records),
                key=lambda item: (item[0], item[1]),
                reverse=True,
            )
            best_score, best_date, record = scored_records[0]
            if best_score < 7:

                return ToolResult(
                    ok=False,
                    error_code="MANDI_ENTITY_MISMATCH",
                    retryable=False,
                    data={"commodity": commodity, "state": state, "district": district, "market": market},
                    source=SourceRecord(
                        name="Government OGD / AGMARKNET",
                        url=url,
                        retrieved_at=datetime.now(timezone.utc),
                        freshness_note="Government dataset returned records, but none matched the requested commodity/location strongly enough.",
                    ),
                )

            tied_best = [
                item for item in scored_records
                if item[0] == best_score and item[1] == best_date
            ]
            if len(tied_best) > 1:
                return ToolResult(
                    ok=False,
                    error_code="MANDI_AMBIGUOUS_MARKET",
                    retryable=False,
                    data={"commodity": commodity, "state": state, "district": district, "market": market},
                    source=SourceRecord(
                        name="Government OGD / AGMARKNET",
                        url=url,
                        retrieved_at=datetime.now(timezone.utc),
                        freshness_note="Multiple records tied on entity match and arrival date; no price was selected.",
                    ),
                )

            def field(*keys: str):
                for key in keys:
                    if record.get(key) not in (None, ""):
                        return record[key]
                return None

            def number(*keys: str) -> float | None:
                for key in keys:
                    value = record.get(key)
                    if value in (None, ""):
                        continue
                    try:
                        return float(str(value).replace(",", "").strip())
                    except ValueError:
                        continue
                return None

            modal = number("Modal_Price", "Modal Price", "modal_price", "Modal_x0020_Price")
            minimum = number("Min_Price", "Min Price", "min_price", "Min_x0020_Price")
            maximum = number("Max_Price", "Max Price", "max_price", "Max_x0020_Price")
            if modal is None:
                return ToolResult(
                    ok=False,
                    error_code="MANDI_INVALID_RECORD",
                    retryable=False,
                    data={"record": record},
                    source=SourceRecord(
                        name="Government OGD / AGMARKNET",
                        url=url,
                        retrieved_at=datetime.now(timezone.utc),
                        freshness_note="Government dataset returned a record without a usable modal price.",
                    ),
                )

            return ToolResult(
                ok=True,
                data={
                    "commodity": field("commodity", "Commodity") or commodity,
                    "market": field("market", "Market") or market or district or state,
                    "district": field("district", "District") or district,
                    "state": field("state", "State") or state,
                    "arrival_date": field("arrival_date", "Arrival_Date"),
                    "min_price": minimum,
                    "modal_price": modal,
                    "max_price": maximum,
                    "unit": "INR/quintal",
                    "raw_record": record,
                },
                source=SourceRecord(
                    name="Government OGD / AGMARKNET",
                    url=url,
                    retrieved_at=datetime.now(timezone.utc),
                    freshness_note="LIVE government market-price response; exact market/date are taken from the returned record.",
                ),
            )
        except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
            return ToolResult(
                ok=False,
                error_code="MANDI_PROVIDER_ERROR",
                retryable=True,
                data={"detail": type(exc).__name__},
            )
