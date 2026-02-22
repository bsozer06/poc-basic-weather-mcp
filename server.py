"""
MCP Weather Server — PoC
========================
Specifikasyona uygun olarak get_weather tool'unu stdio üzerinden sunan MCP sunucusu.
Gerçek bir API yerine, PoC kapsamında simüle edilmiş hava durumu verisi döner.
"""

from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

from mcp.server.fastmcp import FastMCP

# ── MCP Server ────────────────────────────────────────────────────────────────
mcp = FastMCP(name="weather-service")

# ── Simulated weather data (PoC) ─────────────────────────────────────────────
# Gerçek bir API entegrasyonu yerine, PoC'de sabit/rastgele veri kullanıyoruz.
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


def _get_city_weather(city: str, unit: str) -> dict[str, Any]:
    """Return weather data dict conforming to the spec output schema."""
    key = city.strip().lower()
    if key in KNOWN_CITIES:
        temp_c = KNOWN_CITIES[key]["temp_c"]
        condition = KNOWN_CITIES[key]["condition"]
    else:
        # Bilinmeyen şehirler için rastgele ama geçerli veri üret (PoC)
        temp_c = round(random.uniform(-10.0, 40.0), 2)
        condition = random.choice(CONDITIONS)

    temperature: float = temp_c if unit == "celsius" else _celsius_to_fahrenheit(temp_c)

    return {
        "city": city.strip().title(),
        "temperature": float(temperature),
        "unit": unit,
        "condition": condition,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


# ── Tool Definition ──────────────────────────────────────────────────────────
@mcp.tool(
    name="get_weather",
    description="Belirtilen şehir için güncel hava durumu ve sıcaklık bilgisini döner.",
)
def get_weather(city: str, unit: str = "celsius") -> dict[str, Any]:
    """
    Parameters
    ----------
    city : str
        Hava durumu sorgulanacak şehrin adı (örn: Istanbul).
    unit : str, optional
        Sıcaklık birimi — "celsius" veya "fahrenheit". Varsayılan: "celsius".

    Returns
    -------
    dict
        Spec §3'teki şemaya uygun JSON:
        { city, temperature (float), unit, condition (enum), timestamp (ISO8601) }
    """
    # ── Validation (Spec §5 — Schema Validation) ─────────────────────────
    if not city or not city.strip():
        raise ValueError("city parametresi boş olamaz.")

    if not all(c.isalpha() or c.isspace() or c == "-" for c in city.strip()):
        raise ValueError(
            f"Geçersiz şehir adı formatı: '{city}'. "
            "Şehir adı yalnızca harf, boşluk ve tire içerebilir."
        )

    if unit not in ("celsius", "fahrenheit"):
        raise ValueError(
            f"Geçersiz birim: '{unit}'. 'celsius' veya 'fahrenheit' olmalıdır."
        )

    # ── Data retrieval (simulated) ────────────────────────────────────────
    return _get_city_weather(city, unit)


# ── Entry-point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # stdio transport — spec §4 gereği
    mcp.run(transport="stdio")
