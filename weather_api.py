"""
Mock Weather REST API — PoC
============================
Gerçek bir hava durumu API'sini simüle eden FastAPI servisi.
MCP Server (server.py) bu servisi çağırarak veri alır.

Production'da bu servis yerine gerçek bir API (ör: OpenWeatherMap)
kullanılacak — server.py'de sadece base URL değişecek.

Çalıştırma:
    uvicorn weather_api:app --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Query

app = FastAPI(
    title="Weather API (Mock)",
    description="PoC kapsamında hava durumu verisi üreten mock REST API",
    version="1.0.0",
)

# ── Simulated weather data ───────────────────────────────────────────────────
KNOWN_CITIES: dict[str, dict[str, Any]] = {
    "istanbul": {"temp_c": 18.5, "condition": "Cloudy"},
    "ankara": {"temp_c": 12.0, "condition": "Sunny"},
    "izmir": {"temp_c": 22.3, "condition": "Sunny"},
    "london": {"temp_c": 10.2, "condition": "Rainy"},
    "new york": {"temp_c": 5.8, "condition": "Snowy"},
    "tokyo": {"temp_c": 15.0, "condition": "Cloudy"},
    "paris": {"temp_c": 13.7, "condition": "Rainy"},
    "berlin": {"temp_c": 8.4, "condition": "Cloudy"},
}

CONDITIONS = ["Sunny", "Cloudy", "Rainy", "Snowy"]


def _celsius_to_fahrenheit(c: float) -> float:
    return round(c * 9.0 / 5.0 + 32.0, 2)


# ── Endpoints ────────────────────────────────────────────────────────────────
@app.get("/weather")
def get_weather(
    city: str = Query(..., description="Şehir adı (örn: Istanbul)"),
    unit: str = Query("celsius", description="Sıcaklık birimi: celsius | fahrenheit"),
) -> dict[str, Any]:
    """
    Belirtilen şehir için hava durumu verisi döner.

    Returns
    -------
    {
        "city": str,
        "temperature": float,
        "unit": str,
        "condition": "Sunny" | "Cloudy" | "Rainy" | "Snowy",
        "timestamp": "ISO8601"
    }
    """
    # ── Validation ────────────────────────────────────────────────────────
    if not city or not city.strip():
        raise HTTPException(status_code=400, detail="city parametresi boş olamaz.")

    if not all(c.isalpha() or c.isspace() or c == "-" for c in city.strip()):
        raise HTTPException(
            status_code=400,
            detail=f"Geçersiz şehir adı formatı: '{city}'. "
            "Şehir adı yalnızca harf, boşluk ve tire içerebilir.",
        )

    if unit not in ("celsius", "fahrenheit"):
        raise HTTPException(
            status_code=400,
            detail=f"Geçersiz birim: '{unit}'. 'celsius' veya 'fahrenheit' olmalıdır.",
        )

    # ── Data retrieval (simulated) ────────────────────────────────────────
    key = city.strip().lower()
    if key in KNOWN_CITIES:
        temp_c = KNOWN_CITIES[key]["temp_c"]
        condition = KNOWN_CITIES[key]["condition"]
    else:
        temp_c = round(random.uniform(-10.0, 40.0), 2)
        condition = random.choice(CONDITIONS)

    temperature = temp_c if unit == "celsius" else _celsius_to_fahrenheit(temp_c)

    return {
        "city": city.strip().title(),
        "temperature": float(temperature),
        "unit": unit,
        "condition": condition,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    """Servis sağlık kontrolü."""
    return {"status": "ok"}
