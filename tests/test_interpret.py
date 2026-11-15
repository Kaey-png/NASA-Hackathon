from core.interpret import build_trend_response


def test_temperature_trend_uses_temperature_units_and_language():
    result = build_trend_response(
        {
            "MERRA-2": {
                "direction": "up",
                "slope_per_year": 0.05,
                "total_change": 2.0,
                "start_year": 1982,
                "end_year": 2026,
                "years": 44,
                "significant": True,
                "p_value": 0.01,
                "ci_per_year": (0.03, 0.07),
            }
        },
        "temperature",
        "Alabama",
    )

    assert result["results"][0]["badge"] == "Significant warming"
    assert "warming" in result["results"][0]["sentence"]
    assert result["results"][0]["details"]["slope"] == "+0.50 °C per decade"


if __name__ == "__main__":
    test_temperature_trend_uses_temperature_units_and_language()
