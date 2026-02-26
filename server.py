"""
MCP Weather Server — PoC
========================
Specifikasyona uygun olarak get_weather tool'unu stdio üzerinden sunan MCP sunucusu.

Mimari:
  LLM Client  →  MCP Server (bu dosya)  →  REST API (weather_api.py)
                  (protokol adaptörü)        (veri kaynağı)

MCP Server veri üretmez — sadece REST API'ye bağlanır ve sonucu MCP protokolüyle
istemciye iletir. Production'da WEATHER_API_BASE_URL'i gerçek bir API'ye
(ör: OpenWeatherMap) çevirmek yeterlidir.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from mcp.server.fastmcp import FastMCP

# ── Configuration ─────────────────────────────────────────────────────────────
# Production'da bu değeri gerçek API URL'si ile değiştirin.
# Örn: https://api.openweathermap.org/data/2.5  (adaptör katmanı ile)
WEATHER_API_BASE_URL = os.environ.get("WEATHER_API_BASE_URL", "http://127.0.0.1:8000")

# ── MCP Server ────────────────────────────────────────────────────────────────
mcp = FastMCP(name="weather-service")


async def _fetch_weather(city: str, unit: str) -> dict[str, Any]:
    """REST API'den hava durumu verisini çeker."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{WEATHER_API_BASE_URL}/weather",
            params={"city": city, "unit": unit},
        )

    if response.status_code == 400:
        # API validation hatası → MCP tool hatasına çevir
        detail = response.json().get("detail", "Bilinmeyen hata")
        raise ValueError(detail)

    response.raise_for_status()
    return response.json()


# ── Tool Definition ──────────────────────────────────────────────────────────
@mcp.tool(
    name="get_weather",
    description="Belirtilen şehir için güncel hava durumu ve sıcaklık bilgisini döner.",
)
async def get_weather(city: str, unit: str = "celsius") -> dict[str, Any]:
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

    Notes
    -----
    Bu tool, veriyi doğrudan üretmez. Yapılandırılmış REST API'ye (weather_api.py
    veya production API) HTTP isteği atar ve sonucu MCP protokolü ile döner.
    """
    # ── Temel input kontrolü (API'ye gereksiz istek atmasın) ──────────────
    if not city or not city.strip():
        raise ValueError("city parametresi boş olamaz.")

    if unit not in ("celsius", "fahrenheit"):
        raise ValueError(
            f"Geçersiz birim: '{unit}'. 'celsius' veya 'fahrenheit' olmalıdır."
        )

    # ── REST API'den veri çek ─────────────────────────────────────────────
    return await _fetch_weather(city.strip(), unit)


# ── Entry-point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # stdio transport — spec §4 gereği
    mcp.run(transport="stdio")
