from app.orchestrator import _weather_reply


def test_weather_reply_uses_tomorrow_forecast_when_requested():
    reply = _weather_reply(
        {
            "temperature_c": 26,
            "rain_probability_pct": 20,
            "tomorrow_date": "2026-10-12",
            "tomorrow_rain_probability_pct": 75,
            "tomorrow_precipitation_mm": 8.5,
        },
        "कल बारिश होगी?",
    )
    assert "2026-10-12" in reply
    assert "75%" in reply
    assert "8.5 mm" in reply


def test_weather_reply_keeps_24_hour_window_for_general_question():
    reply = _weather_reply(
        {"temperature_c": 26, "rain_probability_pct": 20},
        "बारिश की संभावना कितनी है?",
    )
    assert "20%" in reply
    assert "अगले 24 घंटे" in reply
